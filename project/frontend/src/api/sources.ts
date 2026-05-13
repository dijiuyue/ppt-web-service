import { http } from './client'
import type { SourceFile, UploadSourcesResponse, AddUrlSourceRequest } from '@/types'

export async function getSources(projectId: string): Promise<SourceFile[]> {
  return http.get(`/api/projects/${projectId}/sources`)
}

export async function uploadSources(
  projectId: string,
  files: File[]
): Promise<UploadSourcesResponse> {
  const formData = new FormData()
  files.forEach((file) => formData.append('files', file))

  return http.post(`/api/projects/${projectId}/sources/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (progressEvent) => {
      if (progressEvent.total) {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total)
        console.log('上传进度:', percentCompleted)
      }
    }
  })
}

export async function addUrlSource(
  projectId: string,
  data: AddUrlSourceRequest
): Promise<SourceFile> {
  return http.post(`/api/projects/${projectId}/sources/url`, data)
}

export async function deleteSource(projectId: string, sourceId: string): Promise<void> {
  return http.delete(`/api/projects/${projectId}/sources/${sourceId}`)
}
