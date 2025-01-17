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

from pathlib import Path
from typing import Optional

from aws_cdk.aws_lambda import Tracing, Runtime, RuntimeFamily
from aws_cdk.aws_stepfunctions import IChainable, TaskInput, State
from aws_cdk.core import Construct, Duration

from aws_solutions.cdk.aws_lambda.python.function import SolutionsPythonFunction
from aws_solutions.cdk.cfn_nag import add_cfn_nag_suppressions, CfnNagSuppression
from personalize.aws_lambda.functions.environment import Environment
from personalize.step_functions.personalization_fragment import PersonalizationFragment


class SolutionStep(Construct):
    def __init__(
        self,  # NOSONAR (python:S107) - allow large number of method parameters
        scope: Construct,
        id: str,
        function: str = "lambda_handler",
        entrypoint: Path = None,
        input_path: str = "$",
        result_path: str = "$",
        output_path: str = "$",
        payload: Optional[TaskInput] = None,
        layers=None,
        failure_state: Optional[IChainable] = None,
    ):
        super().__init__(scope, f"{id} Solution Step")

        self.function = self._CreateLambdaFunction(
            self,
            f"{self._snake_case(id)}_fn",
            layers=layers,
            function=function,
            entrypoint=entrypoint,
        )
        add_cfn_nag_suppressions(
            self.function.role.node.try_find_child("DefaultPolicy").node.find_child(
                "Resource"
            ),
            [
                CfnNagSuppression(
                    "W12", "IAM policy for AWS X-Ray requires an allow on *"
                )
            ],
        )

        self._input_path = input_path
        self._result_path = result_path
        self._output_path = output_path
        self._payload = payload
        self._failure_state = failure_state

        self._create_resources()
        self._set_permissions()
        self.environment = self._set_environment()

    def state(
        self,  # NOSONAR (python:S107) - allow large number of method parameters
        scope: Construct,
        construct_id,
        payload: Optional[TaskInput] = None,
        input_path: Optional[str] = None,
        result_path: Optional[str] = None,
        result_selector: Optional[str] = None,
        output_path: Optional[str] = None,
        failure_state: Optional[State] = None,
        **kwargs,
    ):
        payload = payload or self._payload
        input_path = input_path or self._input_path
        result_path = result_path or self._result_path
        output_path = output_path or self._output_path
        failure_state = failure_state or self._failure_state

        return PersonalizationFragment(
            scope,
            construct_id,
            function=self.function,
            payload=payload,
            input_path=input_path,
            result_path=result_path,
            output_path=output_path,
            failure_state=failure_state,
            result_selector=result_selector,
            **kwargs,
        )

    def _snake_case(self, name) -> str:
        return name.replace(" ", "_").lower()

    def _set_permissions(self) -> None:
        raise NotImplementedError("please implement _set_permissions")

    def _create_resources(self) -> None:
        pass  # not required

    def _set_environment(self) -> Environment:
        return Environment(self.function)

    class _CreateLambdaFunction(SolutionsPythonFunction):
        def __init__(self, scope: Construct, construct_id: str, **kwargs):
            entrypoint = kwargs.pop("entrypoint", None)
            if not entrypoint:
                entrypoint = (
                    Path(__file__).absolute().parents[4]
                    / "aws_lambda"
                    / construct_id.replace("_fn", "")
                    / "handler.py"
                )
            libraries = [Path(__file__).absolute().parents[4] / "aws_lambda" / "shared"]
            function = kwargs.pop("function")
            kwargs["layers"] = kwargs.get("layers", [])
            kwargs["tracing"] = Tracing.ACTIVE
            kwargs["timeout"] = Duration.seconds(15)
            kwargs["runtime"] = Runtime("python3.9", RuntimeFamily.PYTHON)

            super().__init__(
                scope,
                construct_id,
                entrypoint,
                function,
                libraries=libraries,
                **kwargs,
            )
