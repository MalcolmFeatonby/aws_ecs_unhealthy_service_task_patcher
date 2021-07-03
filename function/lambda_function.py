import os
import logging
import jsonpickle
import boto3
from datetime import datetime
import pytz

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

ecsClient = boto3.client('ecs')
client = boto3.client('lambda')
client.get_account_settings()

#
# Set to zero ... safe mode. > 0 could result in tasks being stopped.
# !!!CAUTION!!!!
# - Make sure you are very confident with the tasks shown as eligible for termination before making this a number larger than 0.
# - Consider running this with a low number (1) at a low frequency (30 minutes) to build confidence
# !!!CAUTION!!!!
#
MAX_TASKS_STOPPED_PER_RUN = 0 

#
# Maximum time in minutes that tasks must be running before they will be considered
# for remedial action. Set to 25 hours. 
# 
AGE_OF_TASKS_TO_CONSIDER_IN_MINUTES = 1500

total_tasks_to_stopped_this_run = 0
total_unhealth_tasks_identified = 0

def unstick_blocked_task(clusterARN, taskARN, timeRunningInSeconds):

    print('Unsticking blocked Task [' + taskARN + ']')
    response = ecsClient.stop_task(
            cluster=clusterARN, 
            task=taskARN, 
            reason='External health probe noted UNKNOWN health on task with health check but running for [' + str(timeRunningInSeconds / 60) + '] minutes')

    requestId = response['ResponseMetadata']['RequestId']
    responseCode = response['ResponseMetadata']['HTTPStatusCode']

    print('Task [' + taskARN + '] stopped. (RequestId=' + requestId + ', ResponseCode=' + str(responseCode) +')')

    return 1 if responseCode == 200 else 0


## Find all of the Tasks for this Service
def handle_tasks(clusterARN, serviceARN):

  global total_tasks_to_stopped_this_run
  global total_unhealth_tasks_identified

  tasks = ecsClient.list_tasks(cluster=clusterARN, serviceName=serviceARN)

  for taskARN in tasks['taskArns']:
    taskDetail = ecsClient.describe_tasks(cluster=clusterARN, tasks=[taskARN])
    taskHealth = taskDetail['tasks'][0]['healthStatus']
    taskLastState = taskDetail['tasks'][0]['lastStatus']

    if ('startedAt' in taskDetail['tasks'][0]):
      taskStartedAt = taskDetail['tasks'][0]['startedAt']

      rightNow =  datetime.now(pytz.utc)
      timeRunningInSeconds = (rightNow - taskStartedAt.astimezone(pytz.utc)).total_seconds()
      print('Task [' + taskARN + ' is [' + taskHealth + '] and in state [' + taskLastState + '] since [' + taskStartedAt.strftime("%Y-%m-%d %H:%M:%S") + '] Age in seconds (' + str(timeRunningInSeconds) + ')')

      if ('UNKNOWN' == taskHealth and timeRunningInSeconds > (AGE_OF_TASKS_TO_CONSIDER_IN_MINUTES * 60)):
          total_unhealth_tasks_identified += 1
          if (total_tasks_to_stopped_this_run < MAX_TASKS_STOPPED_PER_RUN):
            total_tasks_to_stopped_this_run += unstick_blocked_task(clusterARN, taskARN, timeRunningInSeconds)
          else:
            print('Task [' +taskARN +'] is unhealthy but max tasks per run exceeded.')      

    else:
      print('Task [' + taskARN + ' is not yet running.') 

  return

## Find all of the services in the cluster (we only want to work with tasks launched by services)
def handle_services(clusterARN):

  services = ecsClient.list_services(cluster=clusterARN)
  for serviceARN in services['serviceArns']:

    ## Find the task definition for this service
    serviceDef = ecsClient.describe_services(cluster=clusterARN,services=[serviceARN])

    ## Using the Task Def ARN find the Task Def and determine if we have active health checks 
    taskDefARN = serviceDef['services'][0]['taskDefinition']
    taskDef    = ecsClient.describe_task_definition(taskDefinition=taskDefARN)

    hasActiveHealthCheck = False
    for container in taskDef['taskDefinition']['containerDefinitions']:
       hasActiveHealthCheck = (hasActiveHealthCheck or 'healthCheck' in container)

    ## Services running tasks with active health checks are candidates for remedial action for UNKNOWN health status.
    if hasActiveHealthCheck:
      print('-> Looking for tasks in service [' + serviceARN + ']')
      handle_tasks(clusterARN, serviceARN)
    else:
      print(' -> No active health checks for service [' + serviceARN + ']')

  return


def lambda_handler(event, context):
    logger.info('## ENVIRONMENT VARIABLES\r' + jsonpickle.encode(dict(**os.environ)))
    response = client.get_account_settings()

    print('--Starting workflow-->')

    clusters = ecsClient.list_clusters()

    ## Get a list of all of the clusters for this account

    for clusterARN in clusters['clusterArns']:
      print('-> CLUSTERS [' + clusterARN + ']')
      handle_services(clusterARN)

    print('--Execution completed successfully. [' + str(total_tasks_to_stopped_this_run) + '] tasks stopped, [' + str(total_unhealth_tasks_identified) + '] potentially unhealthy tasks identified.' )

    return "Success" 
