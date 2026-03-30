export type AnnotationVisibility = 'private' | 'cohort' | 'public'
export type AnnotationVisibilitySelection = 'private' | 'cohort'

export interface CareerVideo {
  id: string
  title: string
  topic: string
  durationSeconds: number
  summary: string
  streamUrl: string
  poster: string
  contentType: 'video' | 'article' | 'job_announcement'
  status: 'published' | 'retracted'
  retractedAt: string | null
  retractionNotice: string | null
  jobPostId: string | null
}

export interface ContentItem {
  id: string
  title: string
  content_type: 'video' | 'article' | 'job_announcement'
  media_url?: string | null
  metadata?: Record<string, unknown> | null
  summary?: string | null
  status: 'published' | 'retracted'
  retracted_at?: string | null
  retraction_notice?: string | null
  job_post_id?: string | null
}

export interface StudentApplication {
  id: string
  job_post_id: string
  status: string
  created_at: string
}

export interface CohortOption {
  id: string
  name: string
  slug: string
}

export interface Milestone {
  id: string
  milestone_name: string
  source: string
  progress_value: number
  target_value: number
  achievement_date: string | null
  updated_at: string
}

export interface AnnotationItem {
  id: string
  annotation_text: string | null
  visibility: AnnotationVisibility
  cohort_id: string | null
  updated_at: string
}

export interface BookmarkItem {
  id: string
  content_id: string
  is_favorite: boolean
}

export interface TopicSubscriptionItem {
  id: string
  topic: string
  created_at: string
}

export interface AnnotationSelectionPayload {
  startOffset: number
  endOffset: number
  highlightedText: string
}
