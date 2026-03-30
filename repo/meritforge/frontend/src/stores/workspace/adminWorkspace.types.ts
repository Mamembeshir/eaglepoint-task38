export interface RiskTerm {
  id: string
  term: string
  category: string
  severity: string
  description: string | null
  replacement_suggestion: string | null
  is_active: boolean
  is_regex: boolean
  match_count: number
  created_at: string
}

export interface CohortMember {
  id: string
  email: string
  display_name: string | null
}

export interface CohortWithMembers {
  id: string
  name: string
  slug: string
  description: string | null
  is_admin_defined: boolean
  is_active: boolean
  created_at: string
  members: CohortMember[]
}

export interface AuditLogItem {
  id: string
  action: string
  entity_type: string
  entity_id: string | null
  user_id: string | null
  user_email: string | null
  ip_address: string | null
  description: string | null
  request_url: string | null
  request_method: string | null
  before_data: unknown
  after_data: unknown
  changes: unknown
  created_at: string
}

export interface WebhookConfig {
  id: string
  name: string
  url: string
  events: string[]
  is_active: boolean
  retry_count: number
  retry_delay_seconds: number
  timeout_seconds: number
  created_at: string
}

export interface WebhookDelivery {
  id: string
  webhook_config_id: string
  event_name: string
  status: string
  attempts: number
  response_status: number | null
  last_error: string | null
  queued_at: string
  delivered_at: string | null
  created_at: string
}

export interface WorkflowTemplateStage {
  id: string
  stage_name: string
  stage_order: number
  description: string | null
  is_required: boolean
  is_parallel: boolean
  is_active: boolean
  created_by_id: string | null
  created_at: string
}

export interface WorkflowInitResponse {
  content_id: string
  stages_created: number
  status: string
}

export interface AuditFilters {
  user_email?: string
  action?: string
  start_at?: string
  end_at?: string
}

export interface PublishingHistoryItem {
  id: string
  action: string
  actor_id: string | null
  reason: string | null
  before_state: Record<string, unknown> | null
  after_state: Record<string, unknown> | null
  created_at: string
}

export interface CanaryVisibilityResult {
  content_id: string
  user_id: string
  visible: boolean
  reason: string
}

export interface LegalHoldStatus {
  user_id: string
  legal_hold: boolean
  reason: string | null
  updated_at: string | null
}
