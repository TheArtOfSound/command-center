import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import axios, { type AxiosInstance } from 'axios'

// API key is loaded from localStorage or prompted
let apiKey = localStorage.getItem('qira_api_key') || ''

const api: AxiosInstance = axios.create({ baseURL: '/api' })
api.interceptors.request.use(config => {
  config.headers['X-API-Key'] = apiKey
  return config
})

export function setApiKey(key: string) {
  apiKey = key
  localStorage.setItem('qira_api_key', key)
}

export function getApiKey() { return apiKey }

interface Store {
  view: string
  setView: (v: string) => void
  authenticated: boolean
  setAuthenticated: (v: boolean) => void

  nucleus: any | null
  fetchNucleus: () => Promise<void>

  projects: any[]
  fetchProjects: () => Promise<void>
  updateProject: (id: string, data: any) => Promise<void>
  createProject: (data: any) => Promise<void>

  tasks: any[]
  fetchTasks: (project?: string) => Promise<void>
  createTask: (data: any) => Promise<void>
  updateTask: (id: string, data: any) => Promise<void>
  deleteTask: (id: string) => Promise<void>

  egc: any | null
  fetchEGC: () => Promise<void>

  aronson: any | null
  fetchAronson: () => Promise<void>

  contacts: any[]
  fetchContacts: () => Promise<void>
  createContact: (data: any) => Promise<void>

  today: any | null
  dailyLogs: any[]
  fetchToday: () => Promise<void>
  fetchDailyLogs: () => Promise<void>
  saveDaily: (data: any) => Promise<void>

  ideas: any[]
  fetchIdeas: () => Promise<void>
  createIdea: (data: any) => Promise<void>

  grants: any[]
  fetchGrants: () => Promise<void>

  knowledge: any[]
  fetchKnowledge: (search?: string) => Promise<void>
  searchKnowledge: (q: string) => Promise<any>

  conversations: any[]
  fetchConversations: (search?: string) => Promise<void>

  memories: any[]
  fetchMemories: (project?: string) => Promise<void>

  healthLogs: any[]
  fetchHealthLogs: () => Promise<void>
  addHealthLog: (data: any) => Promise<void>

  chatResponse: string
  chatLoading: boolean
  sendChat: (message: string, mode?: string) => Promise<void>

  liveData: any | null
  fetchLiveData: () => Promise<void>

  links: any[]
  fetchLinks: (project?: string) => Promise<void>
  linkChecks: any[]
  fetchLinkChecks: () => Promise<void>

  githubRepos: any[]
  fetchGithubRepos: () => Promise<void>

  emailTypes: any
  fetchEmailTypes: () => Promise<void>
  emailHistory: any[]
  fetchEmailHistory: () => Promise<void>

  // Session tracking
  sessionStart: string | null
  setSessionStart: (t: string) => void
}

export const useStore = create<Store>()(
  persist(
    (set, get) => ({
      view: 'nucleus',
      setView: (v) => set({ view: v }),
      authenticated: false,
      setAuthenticated: (v) => set({ authenticated: v }),

      nucleus: null,
      fetchNucleus: async () => {
        try {
          const { data } = await api.get('/nucleus')
          set({ nucleus: data })
        } catch {}
      },

      projects: [],
      fetchProjects: async () => {
        try {
          const { data } = await api.get('/projects')
          set({ projects: data })
        } catch {}
      },
      updateProject: async (id, upd) => {
        await api.put(`/projects/${id}`, upd)
        get().fetchProjects()
      },
      createProject: async (d) => {
        await api.post('/projects', d)
        get().fetchProjects()
      },

      tasks: [],
      fetchTasks: async (project) => {
        try {
          const params = project ? { project } : {}
          const { data } = await api.get('/tasks', { params })
          set({ tasks: data })
        } catch {}
      },
      createTask: async (d) => {
        await api.post('/tasks', d)
        get().fetchTasks()
      },
      updateTask: async (id, d) => {
        await api.put(`/tasks/${id}`, d)
        get().fetchTasks()
      },
      deleteTask: async (id) => {
        await api.delete(`/tasks/${id}`)
        get().fetchTasks()
      },

      egc: null,
      fetchEGC: async () => {
        try {
          const { data } = await api.get('/egc/live')
          set({ egc: data })
        } catch {}
      },

      aronson: null,
      fetchAronson: async () => {
        try {
          const { data } = await api.get('/egc/aronson')
          set({ aronson: data })
        } catch {}
      },

      contacts: [],
      fetchContacts: async () => {
        try {
          const { data } = await api.get('/contacts')
          set({ contacts: data })
        } catch {}
      },
      createContact: async (d) => {
        await api.post('/contacts', d)
        get().fetchContacts()
      },

      today: null,
      dailyLogs: [],
      fetchToday: async () => {
        try {
          const { data } = await api.get('/daily/today')
          set({ today: data })
        } catch {}
      },
      fetchDailyLogs: async () => {
        try {
          const { data } = await api.get('/daily')
          set({ dailyLogs: data })
        } catch {}
      },
      saveDaily: async (d) => {
        await api.post('/daily', d)
        get().fetchToday()
        get().fetchDailyLogs()
      },

      ideas: [],
      fetchIdeas: async () => {
        try {
          const { data } = await api.get('/ideas')
          set({ ideas: data })
        } catch {}
      },
      createIdea: async (d) => {
        await api.post('/ideas', d)
        get().fetchIdeas()
      },

      grants: [],
      fetchGrants: async () => {
        try {
          const { data } = await api.get('/grants')
          set({ grants: data })
        } catch {}
      },

      knowledge: [],
      fetchKnowledge: async (search) => {
        try {
          const params = search ? { search } : {}
          const { data } = await api.get('/knowledge', { params })
          set({ knowledge: data })
        } catch {}
      },
      searchKnowledge: async (q) => {
        const { data } = await api.get('/knowledge/search', { params: { q } })
        return data
      },

      conversations: [],
      fetchConversations: async (search) => {
        try {
          const params = search ? { search } : {}
          const { data } = await api.get('/conversations', { params })
          set({ conversations: data })
        } catch {}
      },

      memories: [],
      fetchMemories: async (project) => {
        try {
          const params = project ? { project } : {}
          const { data } = await api.get('/memories', { params })
          set({ memories: data })
        } catch {}
      },

      healthLogs: [],
      fetchHealthLogs: async () => {
        try {
          const { data } = await api.get('/health_logs')
          set({ healthLogs: data })
        } catch {}
      },
      addHealthLog: async (d) => {
        await api.post('/health_logs', d)
        get().fetchHealthLogs()
      },

      chatResponse: '',
      chatLoading: false,
      sendChat: async (message, mode = 'general') => {
        set({ chatLoading: true, chatResponse: '' })
        try {
          const { data } = await api.post('/intelligence/chat', { message, mode })
          set({ chatResponse: data.response })
        } catch {
          set({ chatResponse: 'Connection error — is the backend running on port 7777?' })
        }
        set({ chatLoading: false })
      },

      liveData: null,
      fetchLiveData: async () => {
        try {
          const { data } = await api.get('/live')
          set({ liveData: data })
        } catch {}
      },

      links: [],
      fetchLinks: async (project) => {
        try {
          const params = project ? { project } : {}
          const { data } = await api.get('/links', { params })
          set({ links: data })
        } catch {}
      },
      linkChecks: [],
      fetchLinkChecks: async () => {
        try {
          const { data } = await api.get('/links/check')
          set({ linkChecks: data })
        } catch {}
      },

      githubRepos: [],
      fetchGithubRepos: async () => {
        try {
          const { data } = await api.get('/github/deep/repos')
          if (data && data.length > 0) {
            set({ githubRepos: data })
          } else {
            const { data: fallback } = await api.get('/github/repos')
            set({ githubRepos: fallback })
          }
        } catch {
          try {
            const { data } = await api.get('/github/repos')
            set({ githubRepos: data })
          } catch {}
        }
      },

      emailTypes: {},
      fetchEmailTypes: async () => {
        try {
          const { data } = await api.get('/emails/types')
          set({ emailTypes: data })
        } catch {}
      },
      emailHistory: [],
      fetchEmailHistory: async () => {
        try {
          const { data } = await api.get('/emails/history')
          set({ emailHistory: data })
        } catch {}
      },

      sessionStart: null,
      setSessionStart: (t) => set({ sessionStart: t }),
    }),
    {
      name: 'qira-command-center',
      partialize: (state) => ({
        view: state.view,
        authenticated: state.authenticated,
        sessionStart: state.sessionStart,
      }),
    }
  )
)
