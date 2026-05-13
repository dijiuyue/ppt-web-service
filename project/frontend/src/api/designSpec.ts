import { http } from './client'
import type { DesignSpec, EightConfirmationsData } from '@/types'

export async function getDesignSpec(projectId: string): Promise<DesignSpec> {
  return http.get(`/api/projects/${projectId}/design-spec`)
}

export async function getConfirmations(projectId: string): Promise<DesignSpec> {
  return http.get(`/api/projects/${projectId}/design-spec/confirmations`)
}

export async function confirmEightConfirmations(
  projectId: string,
  data: EightConfirmationsData
): Promise<DesignSpec> {
  return http.post(`/api/projects/${projectId}/design-spec/confirm`, data)
}

export async function updateDesignSpec(
  projectId: string,
  data: Partial<EightConfirmationsData>
): Promise<DesignSpec> {
  return http.put(`/api/projects/${projectId}/design-spec`, data)
}
