# #####################################################################################################################
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.                                                 #
#                                                                                                                     #
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance     #
#  with the License. You may obtain a copy of the License at                                                          #
#                                                                                                                     #
#   http://www.apache.org/licenses/LICENSE-2.0                                                                        #
#                                                                                                                     #
#  Unless required by applicable law or agreed to in writing, software distributed under the License is distributed   #
#  on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for  #
#  the specific language governing permissions and limitations under the License.                                     #
# #####################################################################################################################
from typing import Optional

from aws_cdk.aws_sns import Subscription, SubscriptionProtocol
from aws_cdk.aws_sns import TopicProps
from aws_cdk.aws_stepfunctions import IChainable
from aws_cdk.core import (
    Construct,
    CfnParameter,
    CfnCondition,
    Aspects,
)
from aws_solutions_constructs.aws_lambda_sns import LambdaToSns

from aws_solutions.cdk.aspects import ConditionalResources
from personalize.aws_lambda.functions.solutionstep import SolutionStep


class Notifications(SolutionStep):
    def __init__(
        self,
        scope: Construct,
        id: str,
        email: CfnParameter,
        email_provided: CfnCondition,
        layers=None,
        failure_state: Optional[IChainable] = None,
    ):
        self.email = email
        self.email_provided = email_provided
        self.topic = None  # delay creation until after parent is setup
        self.subscription = None  # delay creation until after parent is setup

        super().__init__(scope, id, layers=layers, failure_state=failure_state)

    def create_sns(self):
        """
        Create the SNS topic using AWS Solutions Constructs
        :return:
        """
        lambda_sns = LambdaToSns(
            self,
            "NotificationConfiguration",
            existing_lambda_obj=self.function,
            topic_props=TopicProps(
                display_name=f"{self.node.try_get_context('SOLUTION_NAME')} Notifications"
            ),
        )
        topic = lambda_sns.sns_topic
        topic.node.default_child.override_logical_id("NotificationTopic")
        return topic

    def create_subscription(self, email, email_provided):
        logical_id = "NotificationSubscription"
        subscription = Subscription(
            self,
            logical_id,
            topic=self.topic,
            endpoint=email.value_as_string,
            protocol=SubscriptionProtocol.EMAIL,
        )
        subscription.node.default_child.override_logical_id(logical_id)
        Aspects.of(subscription).add(ConditionalResources(email_provided))
        return subscription

    def _create_resources(self):
        self.topic = self.create_sns()
        self.subscription = self.create_subscription(
            email=self.email, email_provided=self.email_provided
        )

    def _set_permissions(self) -> None:
        self.topic.grant_publish(self.function)
