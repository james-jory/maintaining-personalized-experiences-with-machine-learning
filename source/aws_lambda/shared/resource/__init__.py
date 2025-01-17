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

from shared.resource.base import Resource
from shared.resource.batch_inference_job import BatchInferenceJob
from shared.resource.campaign import Campaign
from shared.resource.dataset import Dataset
from shared.resource.dataset_group import DatasetGroup
from shared.resource.dataset_import_job import DatasetImportJob
from shared.resource.event_tracker import EventTracker
from shared.resource.filter import Filter
from shared.resource.schema import Schema
from shared.resource.solution import Solution
from shared.resource.solution_version import SolutionVersion


def get_resource(resource_type: str) -> Resource:
    return {
        "datasetGroup": DatasetGroup(),
        "schema": Schema(),
        "dataset": Dataset(),
        "datasetImportJob": DatasetImportJob(),
        "solution": Solution(),
        "solutionVersion": SolutionVersion(),
        "campaign": Campaign(),
        "eventTracker": EventTracker(),
        "filter": Filter(),
        "batchInferenceJob": BatchInferenceJob(),
    }[resource_type]


MANAGED_RESOURCES = [
    DatasetGroup(),
    Schema(),
    Dataset(),
    DatasetImportJob(),
    Solution(),
    SolutionVersion(),
    Campaign(),
    EventTracker(),
    Filter(),
    BatchInferenceJob(),
]
