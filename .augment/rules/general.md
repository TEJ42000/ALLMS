---
type: "manual"
---

We always use task management to ensure that we plan and execute development tasks effectively. We will use the internal
augment code task management system as well as the github issues to track tasks. All tasks should be broken down into 
smaller tasks that can be completed in a single session. Tasks should be assigned to team members and have a clear 
description of the work to be done. Tasks should also have a clear criteria for acceptance. Once a task is complete, 
it should be closed and the work should be merged into the main branch. 

ALl of this work should be managed in github tasks. 

All commits should have comprehensive commit messages that describe the work done in the commit. The commit message should be 
written in the present tense and should be descriptive. The commit message should be written in English. 

# Deployment

## Local Dev Environment

We should use pycharms built in run environments. We have a pycharm mcp which enables this integration.

## Google Cloud Run

We will be deploying this service to google cloud run using the gcloud mcp, you can manage deployment set google cloud project
settings, configure load balancers, etc. using this tool freely. 

The google project to use is vigilant-axis-483119-r8, the region to deploy to is europe-west4.

# Anthropic API

We will be using the anthropic api to power the ai tutor and assessment features of the lls study portal. The api key for this 
project is in the google secret manager under the secret name "anthropic-api-key". The key is in the latest version of the secret. 
You can access this secret using the google cloud console or the gcloud cli. The key should be loaded into the environment 
variable "ANTHROPIC_API_KEY" when running the application.

