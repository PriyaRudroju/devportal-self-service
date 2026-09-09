# Drop-in for BHGitOps/tfc_port_configuration
#
# Copy this file to the repo ROOT (next to blueprints-github.tf).
# Then set the locals below from identifiers in:
#   blueprints-terraform-cloud.tf
#   blueprints-github.tf
#   blueprints-jira.tf
#   ec2-action.tf
#   s3-action.tf
#   feedback.tf
#
# Import existing Home before first apply (one Home per org; do not create):
#   terraform import 'port_page.home' '$home'
#   terraform import port_page.home "\$home"
#
# Provider note: page resource may need PORT_BETA_FEATURES_ENABLED=true
# on the TFC workspace (see versions.tf / providers.tf).
#
# Uncomment once per workspace (dev, then qa, then prod) if you prefer
# config-driven import instead of the CLI, then remove after state has $home:
# import {
#   to = port_page.home
#   id = "$home"
# }

locals {
  # Confirm in blueprints-terraform-cloud.tf (UI title: Terraform-managed EC2)
  home_ec2_blueprint       = "terraformManagedEc2"
  home_ec2_status_property = "status"
  home_ec2_pending_value   = "pending"

  # Confirm in blueprints-github.tf (Port GitHub Ocean default)
  home_github_run_blueprint    = "githubWorkflowRun"
  home_github_run_conclusion   = "conclusion"
  home_github_run_failed_value = "failure"

  # Confirm in blueprints-jira.tf
  home_jira_blueprint       = "jiraIssue"
  home_jira_status_property = "status"
  home_jira_done_value      = "Done"

  # Confirm in *-action.tf / feedback.tf. Set to "" to omit that card.
  home_action_ec2      = "create_ec2"
  home_action_s3       = "create_s3"
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
  description = "BannerHealth landing dashboard: KPI counts, status pies, quick view, and catalog explorers."
  locked      = false

  page_filters = [
    jsonencode({
      identifier = "owning-teams-filter"
      title      = "Owning teams"
      query = {
        combinator = "and"
        rules = [{
          property = "$team"
          operator = "containsAny"
          value    = "{{pageFilter.owningTeams}}"
        }]
      }
    }),
    jsonencode({
      identifier = "environment-filter"
      title      = "Environment"
      query = {
        combinator = "and"
        rules = [{
          property = "environment"
          operator = "="
          value    = "{{pageFilter.environment}}"
        }]
      }
    }),
  ]

  widgets = [
    jsonencode({
      id   = "homeDashboard"
      type = "dashboard-widget"
      layout = [
        {
          height = 180
          columns = [
            { id = "kpiPendingEc2", size = 3 },
            { id = "kpiTfcEc2Total", size = 3 },
            { id = "kpiFailedGithubRuns", size = 3 },
            { id = "kpiOpenJira", size = 3 },
          ]
        },
        {
          height = 400
          columns = [
            { id = "pieEc2Status", size = 4 },
            { id = "pieGithubRunStatus", size = 4 },
            { id = "pieJiraStatus", size = 4 },
          ]
        },
        {
          height = 320
          columns = [
            { id = "quickViewLinks", size = 6 },
            { id = "quickViewActions", size = 6 },
          ]
        },
        {
          height = 320
          columns = [
            { id = "myEntities", size = 4 },
            { id = "recentlyViewed", size = 4 },
            { id = "recentlyUsedActions", size = 4 },
          ]
        },
        {
          height = 420
          columns = [
            { id = "ec2Table", size = 6 },
            { id = "githubRunsTable", size = 6 },
          ]
        },
      ]
      widgets = [
        {
          id             = "kpiPendingEc2"
          type           = "entities-number-chart"
          title          = "Pending EC2"
          icon           = "AWS"
          blueprint      = local.home_ec2_blueprint
          calculationBy  = "entities"
          func           = "count"
          unit           = "custom"
          unitCustom     = "pending"
          dataset = {
            combinator = "and"
            rules = [{
              property = local.home_ec2_status_property
              operator = "="
              value    = local.home_ec2_pending_value
            }]
          }
        },
        {
          id            = "kpiTfcEc2Total"
          type          = "entities-number-chart"
          title         = "TFC EC2 total"
          icon          = "AWS"
          blueprint     = local.home_ec2_blueprint
          calculationBy = "entities"
          func          = "count"
          unit          = "custom"
          unitCustom    = "instances"
        },
        {
          id            = "kpiFailedGithubRuns"
          type          = "entities-number-chart"
          title         = "Failed GitHub runs"
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
          id            = "kpiOpenJira"
          type          = "entities-number-chart"
          title         = "Open Jira"
          icon          = "Jira"
          blueprint     = local.home_jira_blueprint
          calculationBy = "entities"
          func          = "count"
          unit          = "custom"
          unitCustom    = "open"
          dataset = {
            combinator = "and"
            rules = [{
              property = local.home_jira_status_property
              operator = "!="
              value    = local.home_jira_done_value
            }]
          }
        },
        {
          id        = "pieEc2Status"
          type      = "entities-pie-chart"
          title     = "Terraform-managed EC2 by status"
          icon      = "PieChart"
          blueprint = local.home_ec2_blueprint
          property  = "property#${local.home_ec2_status_property}"
          dataset   = { combinator = "and", rules = [] }
        },
        {
          id        = "pieGithubRunStatus"
          type      = "entities-pie-chart"
          title     = "GitHub Workflow Runs by status"
          icon      = "PieChart"
          blueprint = local.home_github_run_blueprint
          property  = "property#${local.home_github_run_conclusion}"
          dataset   = { combinator = "and", rules = [] }
        },
        {
          id        = "pieJiraStatus"
          type      = "entities-pie-chart"
          title     = "Jira issues by status"
          icon      = "PieChart"
          blueprint = local.home_jira_blueprint
          property  = "property#${local.home_jira_status_property}"
          dataset   = { combinator = "and", rules = [] }
        },
        {
          id    = "quickViewLinks"
          type  = "links-widget"
          title = "Quick view"
          icon  = "Link"
          links = [
            { title = "Self-service hub", url = "/self-serve", icon = "Bolt" },
            { title = "Terraform-managed EC2", url = "/${local.home_ec2_blueprint}", icon = "AWS" },
            { title = "GitHub Workflow Runs", url = "/${local.home_github_run_blueprint}", icon = "Github" },
            { title = "Users and teams", url = "/settings/users", icon = "Team" },
          ]
        },
        {
          id      = "quickViewActions"
          type    = "action-card-widget"
          title   = "Self-service"
          icon    = "Bolt"
          actions = local.home_actions
        },
        {
          id    = "myEntities"
          type  = "my-entities"
          title = "My entities"
        },
        {
          id    = "recentlyViewed"
          type  = "recently-viewed-entities"
          title = "Recently viewed entities"
        },
        {
          id    = "recentlyUsedActions"
          type  = "recently-used-actions"
          title = "Recently used actions"
        },
        {
          id        = "ec2Table"
          type      = "table-entities-explorer"
          title     = "Terraform-managed EC2"
          icon      = "AWS"
          blueprint = local.home_ec2_blueprint
          dataset   = { combinator = "and", rules = [] }
        },
        {
          id        = "githubRunsTable"
          type      = "table-entities-explorer"
          title     = "GitHub Workflow Runs"
          icon      = "Github"
          blueprint = local.home_github_run_blueprint
          dataset   = { combinator = "and", rules = [] }
        },
      ]
    }),
  ]
}
