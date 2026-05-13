import { http } from './client'
import type { PPTXExport, CreateExportRequest } from '@/types'

export async function getExports(projectId: string): Promise<PPTXExport[]> {
  return http.get(`/api/projects/${projectId}/exports`)
}

export async function downloadExport(projectId: string, exportId: string): Promise<Blob> {
  const response = await http.get(`/api/projects/${projectId}/exports/${exportId}`, {
    responseType: 'blob'
  })
  return response as unknown as Blob
}

export async function createExport(
  projectId: string,
  data?: CreateExportRequest
): Promise<PPTXExport> {
  return http.post(`/api/projects/${projectId}/exports`, data || {})
}
