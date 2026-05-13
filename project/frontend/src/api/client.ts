import axios, { type AxiosInstance, type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { ElMessage, ElNotification } from 'element-plus'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

export interface ApiResponse<T> {
  data: T
  message?: string
  success: boolean
}

class ApiClient {
  private instance: AxiosInstance

  constructor() {
    this.instance = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json'
      }
    })

    this.setupInterceptors()
  }

  private setupInterceptors() {
    // 请求拦截器
    this.instance.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        const settings = localStorage.getItem('app_settings')
        if (settings) {
          try {
            const parsed = JSON.parse(settings)
            if (parsed.llm_api_key) {
              config.headers['X-LLM-API-Key'] = parsed.llm_api_key
            }
          } catch {
            // 忽略解析错误
          }
        }
        return config
      },
      (error: AxiosError) => {
        return Promise.reject(error)
      }
    )

    // 响应拦截器
    this.instance.interceptors.response.use(
      (response) => {
        // 如果响应是blob类型，直接返回
        if (response.config.responseType === 'blob') {
          return response
        }
        // 如果响应有标准格式，返回data部分
        if (response.data && typeof response.data === 'object' && 'data' in response.data) {
          return response.data.data
        }
        return response.data
      },
      (error: AxiosError) => {
        this.handleError(error)
        return Promise.reject(error)
      }
    )
  }

  private handleError(error: AxiosError) {
    if (error.response) {
      const status = error.response.status
      const data = error.response.data as { detail?: string; message?: string } | undefined
      const message = data?.detail || data?.message || `请求失败 (${status})`

      switch (status) {
        case 400:
          ElMessage.warning(message)
          break
        case 401:
          ElNotification.error({
            title: '未授权',
            message: '请先配置API密钥',
            duration: 3000
          })
          break
        case 403:
          ElNotification.error({
            title: '禁止访问',
            message,
            duration: 3000
          })
          break
        case 404:
          ElMessage.warning('请求的资源不存在')
          break
        case 422:
          ElMessage.warning(`参数错误: ${message}`)
          break
        case 429:
          ElNotification.warning({
            title: '请求过于频繁',
            message: '请稍后再试',
            duration: 3000
          })
          break
        case 500:
          ElNotification.error({
            title: '服务器错误',
            message: '请稍后再试',
            duration: 3000
          })
          break
        default:
          ElMessage.error(message)
      }
    } else if (error.request) {
      ElNotification.error({
        title: '网络错误',
        message: '无法连接到服务器，请检查网络连接',
        duration: 4000
      })
    } else {
      ElMessage.error('请求配置错误')
    }
  }

  getInstance(): AxiosInstance {
    return this.instance
  }
}

const apiClient = new ApiClient()
export const http = apiClient.getInstance()

export default apiClient
