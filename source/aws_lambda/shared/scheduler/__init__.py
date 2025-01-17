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

TASK_PK = "name"
TASK_SK = "version"
CRON_ANY_WILDCARD = "?"
CRON_MIN_MAX_YEAR = (1970, 2199)

from shared.scheduler.base import Scheduler
from shared.scheduler.schedule import Schedule, ScheduleError
from shared.scheduler.task import Task
from shared.scheduler.task_resource import TaskResource
