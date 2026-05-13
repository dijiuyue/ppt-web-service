<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  ElButton,
  ElIcon,
  ElLoading,
  ElEmpty,
  ElMessage,
  ElInput,
  ElTag
} from 'element-plus'
import {
  ArrowLeft,
  ArrowDown,
  Files,
  Edit,
  Check,
  Close,
  Download,
  RefreshLeft
} from '@element-plus/icons-vue'
import { useProjectStore } from '@/stores/project'
import SVGViewer from '@/components/SVGViewer.vue'
import { getSVGContent, updateSVGPage } from '@/api/svgPages'
import type { SVGPage } from '@/types'

const props = defineProps<{
  id: string
}>()

const router = useRouter()
const projectStore = useProjectStore()

const selectedPageId = ref<string>('')
const svgContent = ref<string>('')
const isLoading = ref(false)
const isSaving = ref(false)
const searchQuery = ref('')

const project = computed(() => projectStore.currentProject)
const pages = computed(() => projectStore.svgPages)

const filteredPages = computed(() => {
  if (!searchQuery.value) return pages.value
  const q = searchQuery.value.toLowerCase()
  return pages.value.filter(
    (p: SVGPage) =>
      p.page_name.toLowerCase().includes(q) ||
      String(p.page_number).includes(q)
  )
})

const selectedPage = computed(() => {
  return pages.value.find((p: SVGPage) => p.id === selectedPageId.value) || null
})

onMounted(() => {
  loadPages()
})

const loadPages = async () => {
  isLoading.value = true
  try {
    await projectStore.fetchProject(props.id)
    await projectStore.fetchSVGPages(props.id)
    if (pages.value.length > 0 && !selectedPageId.value) {
      selectedPageId.value = pages.value[0].id
      await loadSVGContent(pages.value[0].id)
    }
  } finally {
    isLoading.value = false
  }
}

const loadSVGContent = async (pageId: string) => {
  isLoading.value = true
  try {
    const content = await getSVGContent(props.id, pageId)
    svgContent.value = content || ''
  } catch {
    svgContent.value = ''
    ElMessage.error('加载 SVG 失败')
  } finally {
    isLoading.value = false
  }
}

const handleSelectPage = async (page: SVGPage) => {
  selectedPageId.value = page.id
  await loadSVGContent(page.id)
}

const handleSaveSVG = async (content: string) => {
  if (!selectedPageId.value) return
  isSaving.value = true
  try {
    await updateSVGPage(props.id, selectedPageId.value, { svg_content: content })
    svgContent.value = content
    ElMessage.success('SVG 已保存')
  } catch {
    ElMessage.error('保存失败')
  } finally {
    isSaving.value = false
  }
}

const handleDownload = () => {
  if (!svgContent.value) return
  const blob = new Blob([svgContent.value], { type: 'image/svg+xml' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = selectedPage.value?.filename || `page_${selectedPageId.value}.svg`
  a.click()
  URL.revokeObjectURL(url)
}

const goBack = () => {
  router.push(`/projects/${props.id}`)
}
</script>

<template>
  <div class="svg-preview-page">
    <!-- 顶部工具栏 -->
    <div class="preview-toolbar">
      <div class="toolbar-left">
        <ElButton link @click="goBack">
          <ElIcon><ArrowLeft /></ElIcon>
          返回
        </ElButton>
        <span class="toolbar-title" v-if="project">{{ project.name }} - SVG 预览</span>
      </div>
      <div class="toolbar-right">
        <ElInput
          v-model="searchQuery"
          placeholder="搜索页面..."
          size="small"
          class="search-input"
          clearable
        />
      </div>
    </div>

    <!-- 主体内容 -->
    <div class="preview-main">
      <!-- 左侧页面列表 -->
      <div class="pages-sidebar">
        <div class="sidebar-header">
          <span class="sidebar-title">
            <ElIcon><Files /></ElIcon>
            页面列表 ({{ pages.length }})
          </span>
        </div>
        <div class="pages-list">
          <div
            v-for="page in filteredPages"
            :key="page.id"
            class="page-list-item"
            :class="{ active: selectedPageId === page.id }"
            @click="handleSelectPage(page)"
          >
            <div class="page-item-header">
              <span class="page-item-number">
                P{{ String(page.page_number).padStart(2, '0') }}
              </span>
              <ElTag
                :type="page.quality_check_status === 'passed' ? 'success' : 'info'"
                size="small"
                class="page-status-tag"
              >
                {{ page.quality_check_status === 'passed' ? '通过' : '待检' }}
              </ElTag>
            </div>
            <span class="page-item-name">{{ page.page_name }}</span>
            <span v-if="page.page_layout" class="page-item-layout">{{ page.page_layout }}</span>
          </div>
          <ElEmpty
            v-if="filteredPages.length === 0"
            description="无匹配页面"
            :image-size="60"
          />
        </div>
      </div>

      <!-- 右侧预览区域 -->
      <div class="preview-content">
        <div v-if="isLoading" v-loading="true" class="preview-loading" />

        <SVGViewer
          v-else-if="selectedPage"
          :page="selectedPage"
          :svg-content="svgContent"
          :editable="true"
          @save="handleSaveSVG"
          @download="handleDownload"
        />

        <ElEmpty v-else description="请选择页面进行预览" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.svg-preview-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - var(--header-height));
  background: var(--bg-secondary);
}

.preview-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  background: var(--bg-primary);
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.toolbar-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.search-input {
  width: 200px;
}

.preview-main {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.pages-sidebar {
  width: 260px;
  flex-shrink: 0;
  background: var(--bg-primary);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
}

.sidebar-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.pages-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.page-list-item {
  padding: 10px 12px;
  border-radius: var(--border-radius-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
  margin-bottom: 4px;
}

.page-list-item:hover {
  background: var(--bg-secondary);
}

.page-list-item.active {
  background: var(--primary-light);
  border-left: 3px solid var(--primary-color);
}

.page-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.page-item-number {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.page-status-tag {
  font-size: 10px;
  padding: 0 6px;
  height: 18px;
  line-height: 16px;
}

.page-item-name {
  font-size: 12px;
  color: var(--text-secondary);
  display: block;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.page-item-layout {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 2px;
}

.preview-content {
  flex: 1;
  overflow: hidden;
  padding: 16px;
}

.preview-loading {
  height: 100%;
  border-radius: var(--border-radius-md);
}

@media (max-width: 768px) {
  .pages-sidebar {
    width: 200px;
  }

  .search-input {
    width: 140px;
  }
}
</style>
