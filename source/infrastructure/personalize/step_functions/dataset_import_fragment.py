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
from typing import List

from aws_cdk.aws_stepfunctions import (
    StateMachineFragment,
    State,
    TaskInput,
    INextable,
    Choice,
    Condition,
    JsonPath,
    Pass,
)
from aws_cdk.core import Construct, Duration

from personalize.aws_lambda.functions import (
    CreateDataset,
    CreateSchema,
    CreateDatasetImportJob,
)


class DatasetImportFragment(StateMachineFragment):
    def __init__(
        self,
        scope: Construct,
        id: str,
        create_schema: CreateSchema,
        create_dataset: CreateDataset,
        create_dataset_import_job: CreateDatasetImportJob,
    ):
        super().__init__(scope, id)
        self.create_schema = create_schema
        self.create_dataset = create_dataset
        self.create_dataset_import_job = create_dataset_import_job

        # total allowed elapsed duration ~ 5h
        retry_config = {
            "backoff_rate": 1.02,
            "interval": Duration.seconds(60),
            "max_attempts": 100,
        }

        # fmt: off
        na_state = Pass(self, f"{id} Not Provided", result_path=JsonPath.DISCARD)
        self._choice = Choice(self, f"Check if {id} Data Configuration Present")

        import_input = {
            "jobName.$": f"States.Format('dataset_import_{id.lower()}_{{}}', $.currentDate)",
            "datasetArn.$": f"$.datasets.{id.lower()}.dataset.serviceConfig.datasetArn",
        }
        import_datasets_from_csv = create_dataset_import_job.state(self, f"Try {id} Dataset Import from CSV",
                                        payload=TaskInput.from_object({
                                            "serviceConfig": {
                                                **import_input,
                                                "dataSource": {
                                                    "dataLocation.$": f"States.Format('s3://{{}}/{{}}/{id.lower()}.csv', $.bucket.name, $.bucket.key)"  # NOSONAR (python:S1192) - string for clarity
                                                },
                                            },
                                            "workflowConfig": {
                                                "maxAge.$": "$.datasetGroup.workflowConfig.maxAge"
                                            }
                                        }),
                                        result_path=JsonPath.DISCARD,
                                        **retry_config)
        import_datasets_from_csv.start_state.add_catch(
            na_state, errors=["NoSuchKey"], result_path=JsonPath.DISCARD
        )
        import_datasets_from_prefix = create_dataset_import_job.state(self, f"Try {id} Dataset Import from Prefix",
                                        payload=TaskInput.from_object({
                                            "serviceConfig": {
                                                **import_input,
                                                "dataSource": {
                                                    "dataLocation.$": f"States.Format('s3://{{}}/{{}}/{id.lower()}', $.bucket.name, $.bucket.key)"  # NOSONAR (python:S1192) - string for clarity
                                                },
                                            },
                                            "workflowConfig": {
                                                "maxAge.$": "$.datasetGroup.workflowConfig.maxAge"
                                            }
                                        }),
                                        result_path=JsonPath.DISCARD,
                                        **retry_config)
        import_datasets_from_prefix.start_state.add_catch(
            import_datasets_from_csv, errors=["NoSuchKey"], result_path=JsonPath.DISCARD
        )

        self._choice.when(Condition.is_present(f"$.datasets.{id.lower()}"),
                          create_schema.state(self, f"Create {id} Schema",
                                              input_path=f"$.datasets.{id.lower()}.schema",
                                              result_path=f"$.datasets.{id.lower()}.schema.serviceConfig")
                          .next(create_dataset.state(self, f"Create {id} Dataset",
                                                     payload=TaskInput.from_object({
                                                         "name.$": f"$.datasets.{id.lower()}.dataset.serviceConfig.name",
                                                         "schemaArn.$": f"$.datasets.{id.lower()}.schema.serviceConfig.schemaArn",
                                                         "datasetGroupArn.$": "$.datasetGroup.serviceConfig.datasetGroupArn",
                                                         "datasetType": f"{id.lower()}",
                                                     }),
                                                     result_path=f"$.datasets.{id.lower()}.dataset.serviceConfig",
                                                     **retry_config))
                          .next(import_datasets_from_prefix))
        self._choice.otherwise(
            na_state
        )
        # fmt: on

    @property
    def start_state(self) -> State:
        return self._choice

    @property
    def end_states(self) -> List[INextable]:
        return [self._choice]
