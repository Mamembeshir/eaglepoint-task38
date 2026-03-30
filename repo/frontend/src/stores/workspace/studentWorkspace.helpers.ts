import type { CareerVideo, ContentItem } from '@/stores/workspace/studentWorkspace.types'

export function mapContentToVideo(item: ContentItem): CareerVideo {
  const metadata = (item.metadata ?? {}) as Record<string, unknown>
  const topic = typeof metadata.topic === 'string' ? metadata.topic : item.content_type.replace('_', '-')
  const durationSeconds = typeof metadata.duration_seconds === 'number'
    ? metadata.duration_seconds
    : Number(metadata.duration_seconds) || 0
  const streamUrl = item.media_url || (typeof metadata.stream_url === 'string' ? metadata.stream_url : '')
  const poster = typeof metadata.poster_url === 'string' ? metadata.poster_url : ''
  const summary = item.summary || (typeof metadata.summary === 'string' ? metadata.summary : '')

  return {
    id: item.id,
    title: item.title,
    topic,
    durationSeconds,
    summary,
    streamUrl,
    poster,
    contentType: item.content_type,
    status: item.status,
    retractedAt: item.retracted_at ?? null,
    retractionNotice: item.retraction_notice ?? null,
    jobPostId: item.job_post_id ?? null
  }
}

export function isUuid(value: string | null | undefined) {
  if (!value) return false
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value)
}
