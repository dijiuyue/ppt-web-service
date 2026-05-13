<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElButton, ElIcon, ElLoading, ElEmpty, ElMessageBox, ElSelect, ElOption } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import { useProjectStore } from '@/stores/project'
import ProjectCard from '@/components/ProjectCard.vue'
import type { Project } from '@/types'

const router = useRouter()
const projectStore = useProjectStore()

const statusFilter = ref('')
const searchQuery = ref('')

const statusOptions = [
  { value: '', label: '全部状态' },
  { value: 'draft', label: '草稿' },
  { value: 'confirming', label: '待确认' },
  { value: 'processing', label: '进行中' },
  { value: 'completed', label: '已完成' },
  { value: 'failed', label: '失败' }
]

const filteredProjects = computed(() => {
  let list = projectStore.projects
  if (statusFilter.value) {
    list = list.filter((p: Project) => p.status === statusFilter.value)
  }
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter(
      (p: Project) =>
        p.name.toLowerCase().includes(q) ||
        (p.description && p.description.toLowerCase().includes(q))
    )
  }
  return list
})

const sortedProjects = computed(() => {
  return [...filteredProjects.value].sort(
    (a: Project, b: Project) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  )
})

const isLoading = computed(() => projectStore.isLoading)

onMounted(() => {
  projectStore.fetchProjects()
})

const goToNewProject = () => {
  router.push('/projects/new')
}

const goToDetail = (id: string) => {
  router.push(`/projects/${id}`)
}

const handleDelete = async (id: string) => {
  try {
    await ElMessageBox.confirm('确定要删除此项目吗？此操作不可恢复。', '删除确认', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await projectStore.deleteProjectById(id)
  } catch {
    // 用户取消
  }
}

const handleStart = (id: string) => {
  projectStore.startProjectPipeline(id)
}

const handleEdit = (id: string) => {
  router.push(`/projects/${id}`)
}
</script>

<template>
  <div class="page-container project-list-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div>
        <h1 class="page-title">项目列表</h1>
        <p class="page-subtitle">管理您的 PPT 生成项目</p>
      </div>
      <ElButton type="primary" size="large" @click="goToNewProject">
        <ElIcon><Plus /></ElIcon>
        新建项目
      </ElButton>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <div class="filter-search">
        <ElIcon class="search-icon"><Search /></ElIcon>
        <input
          v-model="searchQuery"
          class="search-input"
          placeholder="搜索项目名称..."
          type="text"
        />
      </div>
      <ElSelect v-model="statusFilter" placeholder="状态筛选" clearable class="filter-select">
        <ElOption
          v-for="opt in statusOptions"
          :key="opt.value"
          :label="opt.label"
          :value="opt.value"
        />
      </ElSelect>
    </div>

    <!-- 加载状态 -->
    <div v-if="isLoading" v-loading="true" class="loading-container" />

    <!-- 项目卡片网格 -->
    <div v-else-if="sortedProjects.length > 0" class="card-grid">
      <ProjectCard
        v-for="project in sortedProjects"
        :key="project.id"
        :project="project"
        @click="goToDetail"
        @start="handleStart"
        @delete="handleDelete"
        @edit="handleEdit"
      />
    </div>

    <!-- 空状态 -->
    <div v-else class="empty-state">
      <ElEmpty :description="searchQuery || statusFilter ? '没有匹配的项目' : '暂无项目，点击右上角创建'">
        <template #extra>
          <ElButton v-if="!searchQuery && !statusFilter" type="primary" @click="goToNewProject">
            <ElIcon><Plus /></ElIcon>
            创建第一个项目
          </ElButton>
        </template>
      </ElEmpty>
    </div>

    <!-- 统计信息 -->
    <div v-if="sortedProjects.length > 0" class="project-stats">
      <span class="stats-text">
        共 {{ projectStore.projects.length }} 个项目
        <template v-if="filteredProjects.length !== projectStore.projects.length">
          ，当前显示 {{ filteredProjects.length }} 个
        </template>
      </span>
    </div>
  </div>
</template>

<style scoped>
.project-list-page {
  min-height: calc(100vh - var(--header-height) - 48px);
}

.filter-bar {
  display: flex;
  gap: 16px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}

.filter-search {
  flex: 1;
  min-width: 200px;
  max-width: 400px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius-sm);
  transition: border-color var(--transition-fast);
}

.filter-search:focus-within {
  border-color: var(--primary-color);
}

.search-icon {
  color: var(--text-muted);
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: 14px;
  color: var(--text-primary);
}

.search-input::placeholder {
  color: var(--text-muted);
}

.filter-select {
  width: 160px;
}

.loading-container {
  height: 400px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-state {
  padding: 80px 0;
}

.project-stats {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color);
  text-align: center;
}

.stats-text {
  font-size: 13px;
  color: var(--text-muted);
}
</style>
