import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { api } from '@/lib/api'

interface OpsMetricsResponse {
  start_date: string
  end_date: string
  retention: {
    active_users: number
    returning_users: number
    retention_percentage: number
  }
  conversion: {
    interacted_users: number
    applying_users: number
    converted_users: number
    conversion_percentage: number
  }
  funnel: {
    job_posts: number
    applications: number
    milestone_completions: number
    post_to_application_percentage: number
    application_to_milestone_percentage: number
  }
  trend_summaries: Array<{
    event_type: string
    current_total: number
    previous_total: number
    trend_delta: number
    trend_percentage: number
  }>
}

export const useOperationsDashboardStore = defineStore('operations-dashboard', () => {
  const loading = ref(false)
  const startDate = ref(new Date(Date.now() - 1000 * 60 * 60 * 24 * 6).toISOString().slice(0, 10))
  const endDate = ref(new Date().toISOString().slice(0, 10))
  const metrics = ref<OpsMetricsResponse | null>(null)

  const kpis = computed(() => {
    if (!metrics.value) return []
    return [
      {
        key: 'retention',
        label: 'Retention',
        value: `${metrics.value.retention.retention_percentage}%`,
        detail: `${metrics.value.retention.returning_users}/${metrics.value.retention.active_users} returning users`
      },
      {
        key: 'conversion',
        label: 'Conversion',
        value: `${metrics.value.conversion.conversion_percentage}%`,
        detail: `${metrics.value.conversion.converted_users}/${metrics.value.conversion.interacted_users} converted`
      },
      {
        key: 'funnel-a',
        label: 'Post -> Application',
        value: `${metrics.value.funnel.post_to_application_percentage}%`,
        detail: `${metrics.value.funnel.applications}/${metrics.value.funnel.job_posts}`
      },
      {
        key: 'funnel-b',
        label: 'Application -> Milestone',
        value: `${metrics.value.funnel.application_to_milestone_percentage}%`,
        detail: `${metrics.value.funnel.milestone_completions}/${metrics.value.funnel.applications}`
      }
    ]
  })

  async function load() {
    loading.value = true
    try {
      const { data } = await api.get<OpsMetricsResponse>('/api/v1/operations/metrics', {
        params: { start_date: startDate.value, end_date: endDate.value }
      })
      metrics.value = data
    } finally {
      loading.value = false
    }
  }

  function csvExportUrl() {
    const params = new URLSearchParams({ start_date: startDate.value, end_date: endDate.value })
    const base = (api.defaults.baseURL || '').replace(/\/$/, '')
    return `${base}/api/v1/operations/metrics/export.csv?${params.toString()}`
  }

  return {
    loading,
    startDate,
    endDate,
    metrics,
    kpis,
    load,
    csvExportUrl
  }
})
