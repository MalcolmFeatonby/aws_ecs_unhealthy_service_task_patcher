# AWS ECS Unhealthy service task unsticker

The example lambda function shows a mechanism to find all tasks in an account in a region that are in an "UNKNOWN" health state and have container health checks enabled and have been running for an extended period and stop these tasks.

## Rationale

It is possible that these tasks are no longer running but have not yet been stopped by the ECS Scheduler. In some cases it may be possible to know that a task with an "UNKNOWN" health status is in fact unhealthy and for some workload types, like for example stateless workloads, stopping these tasks will cause the ECS Scheduling process to launch a new healthy task.  

## Task termination criteria

Tasks are only considered for termination if:
 * The task has been in the RUNNING state for longer than AGE_OF_TASKS_TO_CONSIDER_IN_MINUTES
 * The task is managed by an ECS Service
 * The task has container health checks configured
 * The task is in an "UNKNOWN" health status
 * In terminating this task the total number of tasks terminated in this run will not exceed MAX_TASKS_STOPPED_PER_RUN 

## Configuration

Three configuration properties are provided in the code:

* AGE_OF_TASKS_TO_CONSIDER_IN_MINUTES - the age in minutes since the task transitioned to RUNNING state. Tasks with an age greater than this value will be checked for health status.
* MAX_TASKS_STOPPED_PER_RUN - the maximum number of tasks that may be stopped in any one iteration of this function. If set to zero (the default) the function will run in "toothless" mode and simply report on the number of Tasks that are considered eligible for termination based on the termination criteria.
* FUZZ_FACTOR - introduces some randomness as to whether to stop a task or not. Lower fuzz factor reduces the likelihood of a Task identified as suspect being stopped. This spreads the tasks that are stopped across a wider set of clusters and makes the algorithm less aggressive. The process honors the MAX_TASKS_STOPPED_PER_RUN which will never be exceeded regardless of FUZZ_FACTOR. FUZZ_FACTOR is a whole integer between 0 and 100 where 100 means stop 100% of identified tasks to the maximum allowed and 0 would mean stop no tasks.

## Caveates  

* The default configuration for this function is reporting only. It will not take distructive action.
* If altered to do so the code will Stop potentially Running ECS Tasks. Make sure that is what you want before changing the configuration to effect this.

## Disclaimer

This function is provided as an example only and should be used as such. There are likely bugs, assume there are :) Feedback is encouraged. If configured to do so it will terminate workloads based on the configuration provided. 

