<script setup lang="ts">
import { BarController, BarElement, CategoryScale, Chart, Legend, LineController, LineElement, PointElement, Tooltip, LinearScale } from 'chart.js'
import { computed, onMounted, ref, watch } from 'vue'

import { UIBadge } from '@/components/ui/badge'
import { UIButton } from '@/components/ui/button'
import { UICard, UICardContent, UICardDescription, UICardHeader, UICardTitle } from '@/components/ui/card'
import { useOperationsDashboardStore } from '@/stores/operationsDashboard'

Chart.register(CategoryScale, LinearScale, BarElement, LineElement, PointElement, Tooltip, Legend, BarController, LineController)

const store = useOperationsDashboardStore()
const trendsCanvas = ref<HTMLCanvasElement | null>(null)
const funnelCanvas = ref<HTMLCanvasElement | null>(null)
let trendsChart: Chart | null = null
let funnelChart: Chart | null = null

const trendRows = computed(() => store.metrics?.trend_summaries ?? [])

function drawCharts() {
  if (!store.metrics || !trendsCanvas.value || !funnelCanvas.value) return

  trendsChart?.destroy()
  funnelChart?.destroy()

  trendsChart = new Chart(trendsCanvas.value, {
    type: 'bar',
    data: {
      labels: trendRows.value.map((row) => row.event_type),
      datasets: [
        {
          label: 'Current Window',
          data: trendRows.value.map((row) => row.current_total),
          backgroundColor: 'rgba(20, 146, 168, 0.75)',
          borderRadius: 8
        },
        {
          label: 'Previous Window',
          data: trendRows.value.map((row) => row.previous_total),
          backgroundColor: 'rgba(107, 114, 128, 0.45)',
          borderRadius: 8
        }
      ]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { position: 'bottom' }
      }
    }
  })

  funnelChart = new Chart(funnelCanvas.value, {
    type: 'line',
    data: {
      labels: ['Job Posts', 'Applications', 'Milestones'],
      datasets: [
        {
          label: 'Funnel Volume',
          data: [
            store.metrics.funnel.job_posts,
            store.metrics.funnel.applications,
            store.metrics.funnel.milestone_completions
          ],
          borderColor: 'rgba(249, 115, 22, 0.9)',
          backgroundColor: 'rgba(249, 115, 22, 0.2)',
          fill: true,
          tension: 0.28
        }
      ]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { position: 'bottom' }
      }
    }
  })
}

async function refresh() {
  await store.load()
  drawCharts()
}

onMounted(refresh)
watch(() => [store.startDate, store.endDate], drawCharts)
</script>

<template>
  <section class="space-y-6">
    <header>
      <p class="text-xs uppercase tracking-[0.16em] text-muted-foreground">Operations Dashboard</p>
      <h2 class="mt-2 text-3xl font-semibold tracking-tight">Performance & Growth Intelligence</h2>
      <p class="mt-1 text-sm text-muted-foreground">Retention, conversion, funnel progression, and trend deltas powered by aggregated telemetry.</p>
    </header>

    <div class="flex flex-wrap items-end gap-3 rounded-xl border border-border/60 bg-card/70 p-3">
      <div>
        <label class="mb-1 block text-xs text-muted-foreground">Start</label>
        <input v-model="store.startDate" type="date" class="h-10 rounded-md border border-input bg-background px-3 text-sm" />
      </div>
      <div>
        <label class="mb-1 block text-xs text-muted-foreground">End</label>
        <input v-model="store.endDate" type="date" class="h-10 rounded-md border border-input bg-background px-3 text-sm" />
      </div>
      <UIButton @click="refresh">Refresh</UIButton>
      <a :href="store.csvExportUrl()" target="_blank" rel="noreferrer">
        <UIButton variant="outline">Export CSV</UIButton>
      </a>
    </div>

    <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      <UICard v-for="kpi in store.kpis" :key="kpi.key" class="border-border/60 bg-card/75">
        <UICardHeader>
          <UICardDescription>{{ kpi.label }}</UICardDescription>
          <UICardTitle class="text-2xl">{{ kpi.value }}</UICardTitle>
        </UICardHeader>
        <UICardContent>
          <p class="text-xs text-muted-foreground">{{ kpi.detail }}</p>
        </UICardContent>
      </UICard>
    </div>

    <div class="grid gap-5 xl:grid-cols-2">
      <UICard class="border-border/60 bg-card/75">
        <UICardHeader>
          <UICardTitle>Trending Events</UICardTitle>
          <UICardDescription>Current vs previous window event counts.</UICardDescription>
        </UICardHeader>
        <UICardContent>
          <canvas ref="trendsCanvas" class="min-h-[260px]" />
          <div class="mt-4 space-y-2">
            <div v-for="row in trendRows" :key="row.event_type" class="flex items-center justify-between text-sm">
              <span class="capitalize">{{ row.event_type.replace('_', ' ') }}</span>
              <UIBadge :variant="row.trend_delta >= 0 ? 'success' : 'outline'">{{ row.trend_delta >= 0 ? '+' : '' }}{{ row.trend_delta }}</UIBadge>
            </div>
          </div>
        </UICardContent>
      </UICard>

      <UICard class="border-border/60 bg-card/75">
        <UICardHeader>
          <UICardTitle>Funnel Progression</UICardTitle>
          <UICardDescription>Job post creation through milestone completion.</UICardDescription>
        </UICardHeader>
        <UICardContent>
          <canvas ref="funnelCanvas" class="min-h-[260px]" />
        </UICardContent>
      </UICard>
    </div>
  </section>
</template>
