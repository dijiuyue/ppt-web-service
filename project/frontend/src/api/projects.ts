import { http } from './client'
import type {
  Project,
  CreateProjectRequest,
  UpdateProjectRequest,
  PaginatedResponse
} from '@/types'

export async function getProjects(
  page = 1,
  pageSize = 20,
  status?: string
): Promise<PaginatedResponse<Project>> {
  const params: Record<string, unknown> = { page, page_size: pageSize }
  if (status) params.status = status
  return http.get('/api/projects', { params })
}

export async function getProject(id: string): Promise<Project> {
  return http.get(`/api/projects/${id}`)
}

export async function createProject(data: CreateProjectRequest): Promise<Project> {
  return http.post('/api/projects', data)
}

export async function updateProject(id: string, data: UpdateProjectRequest): Promise<Project> {
  return http.put(`/api/projects/${id}`, data)
}

export async function deleteProject(id: string): Promise<void> {
  return http.delete(`/api/projects/${id}`)
}

export async function startPipeline(projectId: string): Promise<unknown> {
  return http.post(`/api/projects/${projectId}/start`, {})
}

export async function cancelPipeline(projectId: string): Promise<unknown> {
  return http.post(`/api/projects/${projectId}/cancel`)
}
