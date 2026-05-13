import { http } from './client'
import type { SVGPage, UpdateSVGPageRequest } from '@/types'

export async function getSVGPages(projectId: string): Promise<SVGPage[]> {
  return http.get(`/api/projects/${projectId}/pages`)
}

export async function getSVGPage(projectId: string, pageId: string): Promise<SVGPage> {
  return http.get(`/api/projects/${projectId}/pages/${pageId}`)
}

export async function getSVGContent(projectId: string, pageId: string): Promise<string> {
  return http.get(`/api/projects/${projectId}/pages/${pageId}/svg`, {
    responseType: 'text'
  })
}

export async function updateSVGPage(
  projectId: string,
  pageId: string,
  data: UpdateSVGPageRequest
): Promise<SVGPage> {
  return http.put(`/api/projects/${projectId}/pages/${pageId}`, data)
}
