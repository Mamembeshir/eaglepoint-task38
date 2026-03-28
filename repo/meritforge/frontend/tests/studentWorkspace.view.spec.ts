import { createTestingPinia } from '@pinia/testing'
import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

const workspaceMock = vi.hoisted(() => ({
  videos: [{ id: '11111111-1111-4111-8111-111111111111', title: 'Video A', topic: 'career', durationSeconds: 100, summary: 'A', streamUrl: '/a.mp4', poster: '', contentType: 'video' }],
  currentVideo: { id: '11111111-1111-4111-8111-111111111111', title: 'Video A', topic: 'career', durationSeconds: 100, summary: 'A', streamUrl: '/a.mp4', poster: '', contentType: 'video' },
  currentVideoId: '11111111-1111-4111-8111-111111111111',
  progressByVideo: { '11111111-1111-4111-8111-111111111111': 0 },
  annotationsByVideo: { '11111111-1111-4111-8111-111111111111': [] },
  milestones: [],
  cohorts: [{ id: 'c1', name: 'Alpha', slug: 'alpha' }],
  selectedVisibility: 'private',
  selectedCohortId: '',
  favoriteVideoIds: [],
  subscribedTopics: [],
  privateBookshelf: [],
  hydrateServerState: vi.fn(async () => undefined),
  loadAnnotations: vi.fn(async () => undefined),
  trackPlay: vi.fn(async () => undefined),
  skipCurrentVideo: vi.fn(async () => undefined),
  toggleFavorite: vi.fn(async () => undefined),
  toggleBookmark: vi.fn(async () => undefined),
  toggleTopicSubscription: vi.fn(async () => undefined),
  addAnnotation: vi.fn(async () => undefined),
  selectVideo: vi.fn()
}))

vi.mock('@/stores/studentWorkspace', () => ({
  useStudentWorkspaceStore: () => workspaceMock
}))

import StudentWorkspaceView from '@/views/workspace/StudentWorkspaceView.vue'

describe('StudentWorkspaceView', () => {
  it('hydrates on mount and calls store actions from UI controls', async () => {
    const wrapper = mount(StudentWorkspaceView, {
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
          UITextarea: { template: '<textarea />' }
        }
      }
    })

    await wrapper.vm.$nextTick()
    expect(workspaceMock.hydrateServerState).toHaveBeenCalled()
    expect(workspaceMock.loadAnnotations).toHaveBeenCalledWith(workspaceMock.currentVideo.id)

    const buttonByText = (label: string) =>
      wrapper
        .findAll('button')
        .find((button) => button.text().toLowerCase().includes(label.toLowerCase()))

    await buttonByText('Track play')?.trigger('click')
    await buttonByText('Skip to next')?.trigger('click')
    await buttonByText('Favorite')?.trigger('click')

    expect(workspaceMock.trackPlay).toHaveBeenCalled()
    expect(workspaceMock.skipCurrentVideo).toHaveBeenCalled()
    expect(workspaceMock.toggleFavorite).toHaveBeenCalledWith(workspaceMock.currentVideo.id)
  })
})
