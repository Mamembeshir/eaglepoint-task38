import { createTestingPinia } from '@pinia/testing'
import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

const authState = vi.hoisted(() => ({
  role: 'system_administrator'
}))

const adminStoreMock = vi.hoisted(() => ({
  loadAll: vi.fn(async () => undefined),
  riskTerms: [],
  cohorts: [],
  auditLogs: [],
  webhookDeliveries: [],
  workflowTemplateStages: [],
  publishingHistory: [],
  canaryVisibilityResult: null,
  legalHoldStatus: null,
  createRiskTerm: vi.fn(async () => undefined),
  updateRiskTerm: vi.fn(async () => undefined),
  deleteRiskTerm: vi.fn(async () => undefined),
  createWebhook: vi.fn(async () => undefined),
  retryWebhookDelivery: vi.fn(async () => undefined),
  schedulePublishing: vi.fn(async () => undefined),
  takedownContent: vi.fn(async () => undefined),
  assignUserToCohort: vi.fn(async () => undefined),
  removeUserFromCohort: vi.fn(async () => undefined),
  createWorkflowTemplateStage: vi.fn(async () => undefined),
  initializeContentWorkflow: vi.fn(async () => ({ stages_created: 3 })),
  loadPublishingHistory: vi.fn(async () => undefined),
  checkCanaryVisibility: vi.fn(async () => undefined),
  loadAuditLogs: vi.fn(async () => undefined),
  loadWebhookDeliveries: vi.fn(async () => undefined),
  createCohort: vi.fn(async () => undefined),
  getLegalHoldStatus: vi.fn(async () => ({ legal_hold: false })),
  updateLegalHold: vi.fn(async () => ({ user_id: 'u1', legal_hold: true }))
}))

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => authState
}))

vi.mock('@/stores/adminWorkspace', () => ({
  useAdminWorkspaceStore: () => adminStoreMock
}))

vi.mock('@/lib/stepUp', () => ({
  confirmStepUp: vi.fn(async () => undefined)
}))

import AdminWorkspaceView from '@/views/workspace/AdminWorkspaceView.vue'

describe('AdminWorkspaceView legal hold controls', () => {
  it('renders legal hold controls for admins', async () => {
    authState.role = 'system_administrator'
    const wrapper = mount(AdminWorkspaceView, {
      global: {
        plugins: [createTestingPinia({ createSpy: vi.fn })],
        stubs: {
          UICard: { template: '<div><slot /></div>' },
          UICardHeader: { template: '<div><slot /></div>' },
          UICardTitle: { template: '<div><slot /></div>' },
          UICardDescription: { template: '<div><slot /></div>' },
          UICardContent: { template: '<div><slot /></div>' },
          UIButton: { template: '<button @click="$emit(\'click\')"><slot /></button>' },
          UIBadge: { template: '<span><slot /></span>' },
          UIInput: { props: ['modelValue'], template: '<input v-bind="$attrs" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />' },
          UITextarea: { props: ['modelValue'], template: '<textarea v-bind="$attrs" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />' },
          StepUpConfirmationModal: { template: '<div />' }
        }
      }
    })

    await wrapper.vm.$nextTick()
    const auditTab = wrapper.findAll('button').find((btn) => btn.text().includes('Audit Logs'))
    await auditTab?.trigger('click')
    expect(wrapper.text()).toContain('Legal Hold')
  })

  it('hides legal hold controls for non-admin users', async () => {
    authState.role = 'student'
    const wrapper = mount(AdminWorkspaceView, {
      global: {
        plugins: [createTestingPinia({ createSpy: vi.fn })],
        stubs: {
          UICard: { template: '<div><slot /></div>' },
          UICardHeader: { template: '<div><slot /></div>' },
          UICardTitle: { template: '<div><slot /></div>' },
          UICardDescription: { template: '<div><slot /></div>' },
          UICardContent: { template: '<div><slot /></div>' },
          UIButton: { template: '<button @click="$emit(\'click\')"><slot /></button>' },
          UIBadge: { template: '<span><slot /></span>' },
          UIInput: { props: ['modelValue'], template: '<input v-bind="$attrs" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />' },
          UITextarea: { props: ['modelValue'], template: '<textarea v-bind="$attrs" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />' },
          StepUpConfirmationModal: { template: '<div />' }
        }
      }
    })

    await wrapper.vm.$nextTick()
    const auditTab = wrapper.findAll('button').find((btn) => btn.text().includes('Audit Logs'))
    await auditTab?.trigger('click')
    expect(wrapper.text()).not.toContain('Legal Hold')
  })

  it('calls updateLegalHold when set hold is clicked', async () => {
    authState.role = 'system_administrator'
    const wrapper = mount(AdminWorkspaceView, {
      global: {
        plugins: [createTestingPinia({ createSpy: vi.fn })],
        stubs: {
          UICard: { template: '<div><slot /></div>' },
          UICardHeader: { template: '<div><slot /></div>' },
          UICardTitle: { template: '<div><slot /></div>' },
          UICardDescription: { template: '<div><slot /></div>' },
          UICardContent: { template: '<div><slot /></div>' },
          UIButton: { template: '<button @click="$emit(\'click\')"><slot /></button>' },
          UIBadge: { template: '<span><slot /></span>' },
          UIInput: { props: ['modelValue'], template: '<input v-bind="$attrs" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />' },
          UITextarea: { props: ['modelValue'], template: '<textarea v-bind="$attrs" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />' },
          StepUpConfirmationModal: { template: '<div />' }
        }
      }
    })

    await wrapper.vm.$nextTick()
    const auditTab = wrapper.findAll('button').find((btn) => btn.text().includes('Audit Logs'))
    await auditTab?.trigger('click')

    await wrapper.find('input[placeholder="User ID"]').setValue('11111111-1111-4111-8111-111111111111')
    await wrapper.find('input[placeholder="Reason (optional)"]').setValue('Legal request')
    const setHold = wrapper.findAll('button').find((btn) => btn.text().includes('Set Hold'))
    await setHold?.trigger('click')

    expect(adminStoreMock.updateLegalHold).toHaveBeenCalledWith('11111111-1111-4111-8111-111111111111', {
      legal_hold: true,
      reason: 'Legal request'
    })
  })
})
