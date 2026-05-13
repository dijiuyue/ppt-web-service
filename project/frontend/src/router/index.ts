import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/projects'
  },
  {
    path: '/projects',
    name: 'ProjectList',
    component: () => import('@/views/ProjectList.vue'),
    meta: { title: '项目列表' }
  },
  {
    path: '/projects/new',
    name: 'ProjectNew',
    component: () => import('@/views/ProjectNew.vue'),
    meta: { title: '创建项目' }
  },
  {
    path: '/projects/:id',
    name: 'ProjectDetail',
    component: () => import('@/views/ProjectDetail.vue'),
    meta: { title: '项目详情' },
    props: true
  },
  {
    path: '/projects/:id/confirm',
    name: 'Confirmations',
    component: () => import('@/views/Confirmations.vue'),
    meta: { title: '确认设计规范' },
    props: true
  },
  {
    path: '/projects/:id/pages',
    name: 'SVGPreview',
    component: () => import('@/views/SVGPreview.vue'),
    meta: { title: 'SVG 页面预览' },
    props: true
  },
  {
    path: '/projects/:id/exports',
    name: 'Exports',
    component: () => import('@/views/Exports.vue'),
    meta: { title: '导出管理' },
    props: true
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/Settings.vue'),
    meta: { title: '系统设置' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  }
})

router.beforeEach((to, _from, next) => {
  const title = to.meta.title as string
  if (title) {
    document.title = `${title} - PPT Master`
  } else {
    document.title = 'PPT Master - AI演示文稿生成'
  }
  next()
})

export default router
