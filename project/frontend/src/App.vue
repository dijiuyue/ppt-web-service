<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ElContainer,
  ElHeader,
  ElMain,
  ElMenu,
  ElMenuItem,
  ElButton,
  ElIcon,
  ElBadge,
  ElTooltip
} from 'element-plus'
import {
  HomeFilled,
  FolderOpened,
  Plus,
  Setting,
  MagicStick
} from '@element-plus/icons-vue'
import { useProjectStore } from '@/stores/project'

const route = useRoute()
const router = useRouter()
const projectStore = useProjectStore()

const activeRoute = computed(() => route.path)
const isProcessing = computed(() => projectStore.isPipelineRunning)

const goToProjects = () => router.push('/projects')
const goToNewProject = () => router.push('/projects/new')
const goToSettings = () => router.push('/settings')
</script>

<template>
  <ElContainer class="app-container">
    <!-- 顶部导航栏 -->
    <ElHeader class="app-header" height="var(--header-height)">
      <div class="header-left">
        <div class="logo" @click="goToProjects">
          <ElIcon :size="28" color="var(--primary-color)">
            <MagicStick />
          </ElIcon>
          <span class="logo-text">PPT Master</span>
        </div>
        <nav class="header-nav">
          <ElMenu
            :default-active="activeRoute"
            mode="horizontal"
            class="header-menu"
            :ellipsis="false"
            router
          >
            <ElMenuItem index="/projects" route="/projects">
              <ElIcon><FolderOpened /></ElIcon>
              <span>项目</span>
            </ElMenuItem>
            <ElMenuItem index="/projects/new" route="/projects/new">
              <ElIcon><Plus /></ElIcon>
              <span>新建</span>
            </ElMenuItem>
            <ElMenuItem index="/settings" route="/settings">
              <ElIcon><Setting /></ElIcon>
              <span>设置</span>
            </ElMenuItem>
          </ElMenu>
        </nav>
      </div>
      <div class="header-right">
        <ElTooltip content="有项目正在处理中" v-if="isProcessing">
          <ElBadge is-dot type="primary" class="status-indicator">
            <ElIcon :size="18" class="processing-icon"><MagicStick /></ElIcon>
          </ElBadge>
        </ElTooltip>
        <ElButton
          type="primary"
          size="small"
          class="new-project-btn"
          @click="goToNewProject"
        >
          <ElIcon><Plus /></ElIcon>
          新建项目
        </ElButton>
      </div>
    </ElHeader>

    <!-- 主内容区 -->
    <ElMain class="app-main">
      <router-view v-slot="{ Component }">
        <transition name="page" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </ElMain>
  </ElContainer>
</template>

<style scoped>
.app-container {
  min-height: 100vh;
  background: var(--bg-secondary);
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: var(--bg-primary);
  border-bottom: 1px solid var(--border-color);
  box-shadow: var(--shadow-sm);
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 32px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  transition: opacity var(--transition-fast);
}

.logo:hover {
  opacity: 0.8;
}

.logo-text {
  font-size: 20px;
  font-weight: 700;
  background: linear-gradient(135deg, var(--primary-color) 0%, #7c3aed 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: -0.5px;
}

.header-nav {
  display: flex;
}

.header-menu {
  border-bottom: none;
  background: transparent;
}

.header-menu :deep(.el-menu-item) {
  font-size: 14px;
  font-weight: 500;
  border-bottom: 2px solid transparent;
  height: var(--header-height);
  line-height: var(--header-height);
  color: var(--text-secondary);
}

.header-menu :deep(.el-menu-item.is-active) {
  color: var(--primary-color);
  border-bottom-color: var(--primary-color);
  font-weight: 600;
}

.header-menu :deep(.el-menu-item:hover) {
  color: var(--primary-color);
  background: var(--bg-secondary);
}

.header-menu :deep(.el-icon) {
  margin-right: 4px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.status-indicator {
  cursor: pointer;
}

.processing-icon {
  color: var(--primary-color);
  animation: pulse 2s infinite;
}

.new-project-btn {
  border-radius: 8px;
  font-weight: 500;
}

.app-main {
  padding: 0;
  overflow: visible;
}

/* 页面切换动画 */
.page-enter-active,
.page-leave-active {
  transition: all 250ms ease;
}

.page-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

.page-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

@media (max-width: 768px) {
  .app-header {
    padding: 0 12px;
  }

  .header-left {
    gap: 12px;
  }

  .logo-text {
    font-size: 16px;
  }

  .header-nav {
    display: none;
  }

  .new-project-btn span {
    display: none;
  }
}
</style>
