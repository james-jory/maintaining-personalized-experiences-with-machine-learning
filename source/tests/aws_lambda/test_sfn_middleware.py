# ######################################################################################################################
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.                                                  #
#                                                                                                                      #
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance      #
#  with the License. You may obtain a copy of the License at                                                           #
#                                                                                                                      #
#   http://www.apache.org/licenses/LICENSE-2.0                                                                         #
#                                                                                                                      #
#  Unless required by applicable law or agreed to in writing, software distributed under the License is distributed    #
#  on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for   #
#  the specific language governing permissions and limitations under the License.                                      #
# ######################################################################################################################
import datetime
import logging
from decimal import Decimal

import pytest
from moto import mock_sts

from aws_lambda.shared.sfn_middleware import (
    PersonalizeResource,
    STATUS_IN_PROGRESS,
    STATUS_FAILED,
    ResourcePending,
    ResourceFailed,
    ResourceInvalid,
    json_handler,
    set_defaults,
    set_bucket,
    parse_datetime,
    Parameter,
)


@pytest.fixture
def personalize_resource():
    return PersonalizeResource(
        resource="datasetGroup",
        status="datasetGroup.status",
        config={"name": {"source": "event", "path": "name"}},
    )


def test_personalize_resource_status_active(personalize_resource):
    assert personalize_resource.check_status({"datasetGroup": {"status": "ACTIVE"}})


@pytest.mark.parametrize("status", STATUS_IN_PROGRESS)
def test_personalize_resource_status_pending(status, personalize_resource):
    with pytest.raises(ResourcePending):
        personalize_resource.check_status({"datasetGroup": {"status": status}})


def test_personalize_resource_status_failed(personalize_resource):
    status = STATUS_FAILED

    with pytest.raises(ResourceFailed):
        personalize_resource.check_status({"datasetGroup": {"status": status}})


def test_personalize_status_invalid(personalize_resource):
    with pytest.raises(ResourceInvalid):
        personalize_resource.check_status({"datasetGroup": {}})


@mock_sts
def test_personalize_resource_decorator(personalize_resource, personalize_stubber):
    """
    The typical workflow is to describe, then create, then raise ResourcePending
    """
    dsg_name = "dsgName"
    personalize_stubber.add_client_error(
        "describe_dataset_group", "ResourceNotFoundException"
    )
    personalize_stubber.add_response(
        "create_dataset_group", {}, expected_params={"name": dsg_name}
    )

    @personalize_resource
    def decorated(event, context):
        pass  # NOSONAR (python:S1186) - this is used for mocking

    with pytest.raises(ResourcePending):
        decorated({"name": dsg_name}, None)


@pytest.mark.parametrize(
    "item,serialized",
    [
        (datetime.datetime(2020, 1, 1), "2020-01-01T00:00:00"),
        (Decimal(1), 1),
        (Decimal(1.5), 1.5),
    ],
    ids=[
        "datetime",
        "Decimal integer",
        "Decimal floating point",
    ],
)
def test_json_handler(item, serialized):
    assert json_handler(item) == serialized


def test_set_defaults_1():
    defaults = set_defaults({})
    del defaults["currentDate"]
    del defaults["datasetGroup"]
    assert defaults == {"solutions": []}


def test_set_defaults_2():
    defaults = set_defaults({"solutions": [{}]})
    del defaults["currentDate"]
    del defaults["datasetGroup"]

    assert defaults == {
        "solutions": [
            {"solutionVersions": [], "campaigns": [], "batchInferenceJobs": []}
        ],
    }


def test_set_defaults_3():
    defaults = set_defaults({})
    assert (
        defaults.get("datasetGroup").get("workflowConfig").get("maxAge") == "365 days"
    )


def test_set_defaults_4():
    defaults = set_defaults(
        {"datasetGroup": {"workflowConfig": {"maxAge": "1 second"}}}
    )
    assert defaults["datasetGroup"]["workflowConfig"]["maxAge"] == "1 second"


@pytest.mark.parametrize(
    "bucket,key,expected",
    [
        ("bucket-name", "train/bucket-key.json", "train"),
        ("bucket-name", "train/sub1/bucket-key.json", "train/sub1"),
        ("bucket-name", "train/sub1/sub2/bucket-key.json", "train/sub1/sub2"),
    ],
)
def test_set_bucket(bucket, key, expected):
    config = {}
    result = set_bucket(config, bucket, key)

    assert result["bucket"]["name"] == bucket
    assert result["bucket"]["key"] == expected


@pytest.mark.parametrize(
    "time_string,seconds",
    [
        ("1 day", 86400),
        ("two days", 86400 * 2),
        ("0.5 days", 86400 / 2),
        ("1 week", 86400 * 7),
        ("1 month", 86400 * 31),  # there were 31 days in January 1 CE
        (
            "1 year",
            86400 * 365,
        ),  # going higher than 3 years will result in off-by-one-day errors
    ],
)
def test_parse_datetime(time_string, seconds, caplog):
    with caplog.at_level(logging.WARNING):
        assert parse_datetime(time_string) == seconds
        if "month" in time_string or "year" in time_string:
            assert (
                "they are based off of the calendar of the start of year 1 CE"
                in caplog.text
            )


@pytest.mark.parametrize(
    "key,source,path,format_as,default,result",
    [
        ("key_a", "event", "key_a", None, None, "value_a"),
        ("key_b", "environment", "SOLUTION_VERSION", None, None, "v99.99.99"),
        ("key_c", "event", "key_c", "string", None, '{"some": "json"}'),
        ("key_d", "event", "key_d", "seconds", None, 5),
        ("key_e", "event", "key_e", None, "value_e", "value_e"),
        ("key_f", "event", "key_f", "seconds", "one week", 604800),
        ("key_g", "event", "key_g", None, "omit", None),
    ],
)
def test_parameter_resolution(key, source, path, format_as, default, result):
    event = {
        "key_a": "value_a",
        "key_c": {"some": "json"},
        "key_d": "five seconds",
        "key_g": "",
    }

    assert (
        Parameter(
            key=key,
            source=source,
            path=path,
            format_as=format_as,
            default=default,
        ).resolve(event)
        == result
    )
