# Drop-in for BHGitOps/tfc_port_configuration
#
# Copy to the repo ROOT (next to blueprints-github.tf).
# Confirm locals against blueprint-self-service.tf / blueprints-github.tf /
# blueprints-jira.tf / variables.tf (action identifiers).
#
# Import existing Home before first apply:
#   terraform import 'port_page.home' '$home'
#
# Does not change the Organization sidebar or Dev/QA/Prod org switcher.

locals {
  home_ss_blueprint         = "selfServiceInfraResources"
  home_ss_resource_property = "resource"
  home_ss_ec2_value         = "ec2"
  home_ss_s3_value          = "s3"
  home_ss_status_property   = "provisioning_status"
  home_ss_provisioned_value = "provisioned"

  home_github_run_blueprint    = "githubWorkflowRun"
  home_github_run_conclusion   = "conclusion"
  home_github_run_failed_value = "failure"

  home_jira_blueprint       = "jiraIssue"
  home_jira_status_property = "status"
  home_jira_done_value      = "Done"

  # In tfc_port_configuration these should be var.ec2_instance_create_action_identifier etc.
  home_action_ec2      = "create_ec2_instance"
  home_action_s3       = "create_s3_bucket"
  home_action_feedback = "submit_feedback"

  home_actions = compact([
    local.home_action_ec2,
    local.home_action_s3,
    local.home_action_feedback,
  ])
}

resource "port_page" "home" {
  identifier  = "$home"
  title       = "Home"
  icon        = "Home"
  type        = "home"
  description = "BannerHealth Home: provisioned KPIs, pies, three self-service actions, and recently viewed."
  locked      = false

  widgets = [
    jsonencode({
      id   = "homeDashboard"
      type = "dashboard-widget"
      layout = [
        {
          height = 200
          columns = [
            { id = "quickViewLinks", size = 12 },
          ]
        },
        {
          height = 180
          columns = [
            { id = "kpiProvisionedEc2", size = 3 },
            { id = "kpiProvisionedS3", size = 3 },
            { id = "kpiFailedGithubRuns", size = 3 },
            { id = "kpiCompletedJira", size = 3 },
          ]
        },
        {
          height = 400
          columns = [
            { id = "pieEc2Status", size = 4 },
            { id = "pieS3Status", size = 4 },
            { id = "pieGithubRunStatus", size = 4 },
          ]
        },
        {
          height = 220
          columns = [
            { id = "quickActions", size = 12 },
          ]
        },
        {
          height = 320
          columns = [
            { id = "recentlyViewed", size = 12 },
          ]
        },
      ]
      widgets = [
        {
          id    = "quickViewLinks"
          type  = "links-widget"
          title = "Quick view"
          icon  = "Link"
          links = [
            { title = "Self-service hub", url = "/self-serve", icon = "Bolt" },
            { title = "Self Service Infra Resources", url = "/${local.home_ss_blueprint}", icon = "Server" },
            { title = "GitHub Workflow Runs", url = "/${local.home_github_run_blueprint}", icon = "Github" },
            { title = "Users and teams", url = "/settings/users", icon = "Team" },
          ]
        },
        {
          id             = "kpiProvisionedEc2"
          type           = "entities-number-chart"
          title          = "Provisioned EC2"
          icon           = "AWS"
          blueprint      = local.home_ss_blueprint
          calculationBy  = "entities"
          func           = "count"
          unit           = "custom"
          unitCustom     = "instances"
          dataset = {
            combinator = "and"
            rules = [
              { property = local.home_ss_resource_property, operator = "=", value = local.home_ss_ec2_value },
              { property = local.home_ss_status_property, operator = "=", value = local.home_ss_provisioned_value },
            ]
          }
        },
        {
          id             = "kpiProvisionedS3"
          type           = "entities-number-chart"
          title          = "Provisioned S3"
          icon           = "AWS"
          blueprint      = local.home_ss_blueprint
          calculationBy  = "entities"
          func           = "count"
          unit           = "custom"
          unitCustom     = "buckets"
          dataset = {
            combinator = "and"
            rules = [
              { property = local.home_ss_resource_property, operator = "=", value = local.home_ss_s3_value },
              { property = local.home_ss_status_property, operator = "=", value = local.home_ss_provisioned_value },
            ]
          }
        },
        {
          id            = "kpiFailedGithubRuns"
          type          = "entities-number-chart"
          title         = "Failed Workflow Runs"
          icon          = "Github"
          blueprint     = local.home_github_run_blueprint
          calculationBy = "entities"
          func          = "count"
          unit          = "custom"
          unitCustom    = "failed"
          dataset = {
            combinator = "and"
            rules = [{
              property = local.home_github_run_conclusion
              operator = "="
              value    = local.home_github_run_failed_value
            }]
          }
        },
        {
          id            = "kpiCompletedJira"
          type          = "entities-number-chart"
          title         = "Completed Tasks"
          icon          = "Jira"
          blueprint     = local.home_jira_blueprint
          calculationBy = "entities"
          func          = "count"
          unit          = "custom"
          unitCustom    = "done"
          dataset = {
            combinator = "and"
            rules = [{
              property = local.home_jira_status_property
              operator = "="
              value    = local.home_jira_done_value
            }]
          }
        },
        {
          id        = "pieEc2Status"
          type      = "entities-pie-chart"
          title     = "EC2 by Status"
          icon      = "PieChart"
          blueprint = local.home_ss_blueprint
          property  = "property#${local.home_ss_status_property}"
          dataset = {
            combinator = "and"
            rules = [{ property = local.home_ss_resource_property, operator = "=", value = local.home_ss_ec2_value }]
          }
        },
        {
          id        = "pieS3Status"
          type      = "entities-pie-chart"
          title     = "S3 by Status"
          icon      = "PieChart"
          blueprint = local.home_ss_blueprint
          property  = "property#${local.home_ss_status_property}"
          dataset = {
            combinator = "and"
            rules = [{ property = local.home_ss_resource_property, operator = "=", value = local.home_ss_s3_value }]
          }
        },
        {
          id        = "pieGithubRunStatus"
          type      = "entities-pie-chart"
          title     = "Workflow Runs by Conclusion"
          icon      = "PieChart"
          blueprint = local.home_github_run_blueprint
          property  = "property#${local.home_github_run_conclusion}"
          dataset   = { combinator = "and", rules = [] }
        },
        {
          id      = "quickActions"
          type    = "action-card-widget"
          title   = "Quick Actions"
          icon    = "Bolt"
          actions = local.home_actions
        },
        {
          id    = "recentlyViewed"
          type  = "recently-viewed-entities"
          title = "Recently viewed entities"
        },
      ]
    }),
  ]
}
