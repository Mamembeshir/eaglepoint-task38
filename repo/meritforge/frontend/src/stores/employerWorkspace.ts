import { defineStore } from 'pinia'
import { ref } from 'vue'

import { api } from '@/lib/api'
import { getApiErrorMessage } from '@/lib/apiErrors'

interface JobPost {
  id: string
  content_id: string
  title: string
  employer_name: string
  location: string | null
  employment_type: string | null
  application_deadline: string | null
  is_active: boolean
  created_at: string
}

interface Application {
  id: string
  job_post_id: string
  applicant_id: string
  status: string
  submitted_at: string | null
  reviewed_at: string | null
  created_at: string
}

interface Milestone {
  id: string
  student_id: string
  application_id: string | null
  milestone_name: string
  progress_value: number
  target_value: number
  is_verified: boolean
  updated_at: string
}

interface MilestoneTemplatePayload {
  key: string
  name: string
  description?: string
  threshold_count?: number
}

interface UserProfilePreview {
  id: string
  email: string | null
  first_name: string | null
  last_name: string | null
  display_name: string | null
  avatar_url: string | null
  phone_number: string | null
}

export const useEmployerWorkspaceStore = defineStore('employer-workspace', () => {
  const loading = ref(false)
  const posts = ref<JobPost[]>([])
  const selectedPostId = ref<string>('')
  const applications = ref<Application[]>([])
  const milestones = ref<Milestone[]>([])
  const applicantProfiles = ref<Record<string, UserProfilePreview | null>>({})
  const profileErrors = ref<Record<string, string>>({})

  async function loadPosts() {
    loading.value = true
    try {
      const { data } = await api.get<JobPost[]>('/api/v1/employer/job-posts')
      posts.value = data
      if (!selectedPostId.value && data.length) selectedPostId.value = data[0].id
    } finally {
      loading.value = false
    }
  }

  async function createPost(payload: {
    title: string
    employer_name: string
    description?: string
    location?: string
    employment_type?: string
    application_deadline?: string
  }) {
    await api.post('/api/v1/employer/job-posts', payload)
    await loadPosts()
  }

  async function loadSelectedPostDetails() {
    if (!selectedPostId.value) {
      applications.value = []
      milestones.value = []
      return
    }

    const [appsRes, milestonesRes] = await Promise.all([
      api.get<Application[]>(`/api/v1/employer/job-posts/${selectedPostId.value}/applications`),
      api.get<Milestone[]>(`/api/v1/employer/job-posts/${selectedPostId.value}/milestones`)
    ])
    applications.value = appsRes.data
    milestones.value = milestonesRes.data

    await Promise.all(
      applications.value.map(async (application) => {
        try {
          const { data } = await api.get<UserProfilePreview>(`/api/v1/users/${application.applicant_id}`)
          applicantProfiles.value[application.applicant_id] = data
          delete profileErrors.value[application.applicant_id]
        } catch (error) {
          applicantProfiles.value[application.applicant_id] = null
          profileErrors.value[application.applicant_id] = getApiErrorMessage(error)
        }
      })
    )
  }

  function profileDisplayName(userId: string): string {
    const profile = applicantProfiles.value[userId]
    if (!profile) return `${userId.slice(0, 8)}...`
    return profile.display_name || [profile.first_name, profile.last_name].filter(Boolean).join(' ') || `${userId.slice(0, 8)}...`
  }

  async function updateApplicationStatus(applicationId: string, status: string, notes?: string) {
    await api.patch(`/api/v1/employer/applications/${applicationId}/status`, { status, notes })
    await loadSelectedPostDetails()
  }

  async function verifyMilestone(milestoneId: string, isVerified: boolean, note?: string) {
    await api.patch(`/api/v1/employer/milestones/${milestoneId}/verify`, {
      is_verified: isVerified,
      note
    })
    await loadSelectedPostDetails()
  }

  async function createMilestoneTemplate(payload: MilestoneTemplatePayload) {
    if (!selectedPostId.value) return
    await api.post(`/api/v1/employer/job-posts/${selectedPostId.value}/milestone-templates`, payload)
    await loadSelectedPostDetails()
  }

  return {
    loading,
    posts,
    selectedPostId,
    applications,
    milestones,
    applicantProfiles,
    profileErrors,
    loadPosts,
    createPost,
    loadSelectedPostDetails,
    updateApplicationStatus,
    verifyMilestone,
    createMilestoneTemplate,
    profileDisplayName
  }
})
