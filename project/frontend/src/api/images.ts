import { http } from './client'
import type { ImageResource, UpdateImageRequest } from '@/types'

export async function getImages(projectId: string): Promise<ImageResource[]> {
  return http.get(`/api/projects/${projectId}/images`)
}

export async function uploadImage(
  projectId: string,
  file: File,
  purpose?: string
): Promise<ImageResource> {
  const formData = new FormData()
  formData.append('file', file)
  if (purpose) formData.append('purpose', purpose)

  return http.post(`/api/projects/${projectId}/images/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export async function updateImage(
  projectId: string,
  imageId: string,
  data: UpdateImageRequest
): Promise<ImageResource> {
  return http.put(`/api/projects/${projectId}/images/${imageId}`, data)
}
