import axios from 'axios'
import { resReject, resResolve, reqReject, reqResolve } from './interceptors'

export function createAxios(options = {}) {
  const defaultOptions = {
    timeout: 12000,
  }
  const service = axios.create({
    ...defaultOptions,
    ...options,
  })
  service.interceptors.request.use(reqResolve, reqReject)
  service.interceptors.response.use(resResolve, resReject)
  return service
}

const axiosInstance = createAxios({
  baseURL: import.meta.env.VITE_BASE_API,
})

// 为了兼容性同时导出两个名称
export const defHttp = axiosInstance
export const request = axiosInstance
