import { http } from './client'
import type { PipelineStatus, PipelineJob } from '@/types'

export async function getPipelineStatus(projectId: string): Promise<PipelineStatus> {
  return http.get(`/api/projects/${projectId}/pipeline/status`)
}

export async function getPipelineJobs(projectId: string): Promise<PipelineJob[]> {
  return http.get(`/api/projects/${projectId}/pipeline/jobs`)
}

export async function resumePipeline(projectId: string): Promise<unknown> {
  return http.post(`/api/projects/${projectId}/pipeline/resume`)
}
