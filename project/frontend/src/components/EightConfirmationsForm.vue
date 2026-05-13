<script setup lang="ts">
import { reactive, watch } from 'vue'
import {
  ElForm,
  ElFormItem,
  ElInput,
  ElInputNumber,
  ElSelect,
  ElOption,
  ElColorPicker,
  ElButton,
  ElCard,
  ElRow,
  ElCol,
  ElIcon,
  ElTooltip
} from 'element-plus'
import {
  Monitor,
  Files,
  User,
  Brush,
  Palette,
  CollectionTag,
  FontSize,
  Picture,
  CircleCheck
} from '@element-plus/icons-vue'
import type { EightConfirmationsData, ColorScheme, Typography } from '@/types'

const props = defineProps<{
  initialData?: Partial<EightConfirmationsData>
  loading?: boolean
}>()

const emit = defineEmits<{
  (e: 'submit', data: EightConfirmationsData): void
}>()

const form = reactive<EightConfirmationsData>({
  confirmation_canvas: 'ppt169',
  confirmation_page_count: 12,
  confirmation_audience: '',
  confirmation_style_mode: 'A',
  confirmation_style_descriptor: '',
  confirmation_color_scheme: {
    primary: '#4f6ef7',
    secondary: '#6b7280',
    accent: '#f59e0b',
    background: '#ffffff',
    text: '#1f2937',
    text_secondary: '#6b7280'
  },
  confirmation_icon_approach: 'A',
  confirmation_typography: {
    title_font: 'Noto Sans SC',
    body_font: 'Noto Sans SC',
    title_size: '36px',
    body_size: '16px'
  },
  confirmation_image_approach: 'C'
})

watch(
  () => props.initialData,
  (data) => {
    if (data) {
      Object.assign(form, data)
    }
  },
  { immediate: true, deep: true }
)

const canvasOptions = [
  { value: 'ppt169', label: 'PPT 16:9 (1280x720)', desc: '标准演示文稿格式' },
  { value: 'ppt43', label: 'PPT 4:3 (1024x768)', desc: '传统演示文稿格式' },
  { value: 'xhs', label: '小红书 (720x960)', desc: '社交媒体卡片格式' },
  { value: 'story', label: 'Story (540x960)', desc: '竖屏故事格式' }
]

const styleModeOptions = [
  { value: 'A', label: 'A - 极简商务', desc: '简洁、专业、大量留白，适合商务汇报' },
  { value: 'B', label: 'B - 视觉冲击力', desc: '大胆用色、强烈对比，适合品牌展示' },
  { value: 'C', label: 'C - 温暖人文', desc: '柔和色调、亲和力强，适合教育培训' }
]

const iconApproachOptions = [
  { value: 'A', label: 'A - 线性图标', desc: '简洁线条风格，现代感强' },
  { value: 'B', label: 'B - 面性图标', desc: '填充色块风格，识别度高' },
  { value: 'C', label: 'C - 双色图标', desc: '双色渐变风格，视觉丰富' },
  { value: 'D', label: 'D - 插画风格', desc: '手绘插画风格，活泼有趣' }
]

const imageApproachOptions = [
  { value: 'A', label: 'A - AI生成', desc: '使用AI生成所有图片，风格统一' },
  { value: 'B', label: 'B - 网络搜索', desc: '从网络搜索图片，选择丰富' },
  { value: 'C', label: 'C - 混合模式', desc: 'AI生成+网络搜索，灵活搭配' },
  { value: 'D', label: 'D - 用户上传', desc: '使用用户上传的图片' },
  { value: 'E', label: 'E - 纯图标', desc: '仅使用图标，无图片' }
]

const fontOptions = [
  { value: 'Noto Sans SC', label: 'Noto Sans SC (默认)' },
  { value: 'PingFang SC', label: 'PingFang SC (苹方)' },
  { value: 'Microsoft YaHei', label: 'Microsoft YaHei (微软雅黑)' },
  { value: 'SimHei', label: 'SimHei (黑体)' },
  { value: 'SimSun', label: 'SimSun (宋体)' },
  { value: 'Helvetica Neue', label: 'Helvetica Neue' },
  { value: 'Arial', label: 'Arial' },
  { value: 'Georgia', label: 'Georgia' }
]

const handleColorChange = (key: keyof ColorScheme, color: string) => {
  form.confirmation_color_scheme[key] = color
}

const handleSubmit = () => {
  emit('submit', { ...form })
}
</script>

<template>
  <div class="confirmations-form">
    <!-- 1. Canvas Format -->
    <ElCard class="form-section">
      <template #header>
        <div class="section-header">
          <ElIcon :size="18" color="var(--primary-color)"><Monitor /></ElIcon>
          <span>1. 画布格式 (Canvas Format)</span>
        </div>
      </template>
      <ElFormItem label="选择画布格式" required>
        <ElSelect v-model="form.confirmation_canvas" class="full-width">
          <ElOption
            v-for="opt in canvasOptions"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          >
            <div class="select-option">
              <span>{{ opt.label }}</span>
              <span class="option-desc">{{ opt.desc }}</span>
            </div>
          </ElOption>
        </ElSelect>
      </ElFormItem>
    </ElCard>

    <!-- 2. Page Count -->
    <ElCard class="form-section">
      <template #header>
        <div class="section-header">
          <ElIcon :size="18" color="var(--primary-color)"><Files /></ElIcon>
          <span>2. 页数 (Page Count)</span>
        </div>
      </template>
      <ElFormItem label="目标页数" required>
        <ElInputNumber
          v-model="form.confirmation_page_count"
          :min="1"
          :max="50"
          :step="1"
          class="page-count-input"
        />
        <span class="input-hint">建议范围: 5-20 页</span>
      </ElFormItem>
    </ElCard>

    <!-- 3. Target Audience -->
    <ElCard class="form-section">
      <template #header>
        <div class="section-header">
          <ElIcon :size="18" color="var(--primary-color)"><User /></ElIcon>
          <span>3. 目标受众 (Target Audience)</span>
        </div>
      </template>
      <ElFormItem label="受众描述" required>
        <ElInput
          v-model="form.confirmation_audience"
          type="textarea"
          :rows="3"
          placeholder="例如: 技术团队高管，有5年以上行业经验，关注ROI和技术可行性"
        />
      </ElFormItem>
    </ElCard>

    <!-- 4. Style Mode -->
    <ElCard class="form-section">
      <template #header>
        <div class="section-header">
          <ElIcon :size="18" color="var(--primary-color)"><Brush /></ElIcon>
          <span>4. 风格模式 (Style Mode)</span>
        </div>
      </template>
      <ElFormItem label="风格选择" required>
        <ElSelect v-model="form.confirmation_style_mode" class="full-width">
          <ElOption
            v-for="opt in styleModeOptions"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          >
            <div class="select-option">
              <span>{{ opt.label }}</span>
              <span class="option-desc">{{ opt.desc }}</span>
            </div>
          </ElOption>
        </ElSelect>
      </ElFormItem>
      <ElFormItem label="风格描述补充">
        <ElInput
          v-model="form.confirmation_style_descriptor"
          type="textarea"
          :rows="2"
          placeholder="补充描述您期望的视觉风格..."
        />
      </ElFormItem>
    </ElCard>

    <!-- 5. Color Scheme -->
    <ElCard class="form-section">
      <template #header>
        <div class="section-header">
          <ElIcon :size="18" color="var(--primary-color)"><Palette /></ElIcon>
          <span>5. 配色方案 (Color Scheme)</span>
        </div>
      </template>
      <ElRow :gutter="16">
        <ElCol :span="12" :xs="24">
          <ElFormItem label="主色 (Primary)">
            <div class="color-picker-row">
              <ElColorPicker
                :model-value="form.confirmation_color_scheme.primary"
                @update:model-value="(c) => handleColorChange('primary', c)"
                show-alpha
              />
              <ElInput
                :model-value="form.confirmation_color_scheme.primary"
                @update:model-value="(c) => handleColorChange('primary', c)"
                class="color-input"
              />
            </div>
          </ElFormItem>
        </ElCol>
        <ElCol :span="12" :xs="24">
          <ElFormItem label="辅色 (Secondary)">
            <div class="color-picker-row">
              <ElColorPicker
                :model-value="form.confirmation_color_scheme.secondary"
                @update:model-value="(c) => handleColorChange('secondary', c)"
                show-alpha
              />
              <ElInput
                :model-value="form.confirmation_color_scheme.secondary"
                @update:model-value="(c) => handleColorChange('secondary', c)"
                class="color-input"
              />
            </div>
          </ElFormItem>
        </ElCol>
        <ElCol :span="12" :xs="24">
          <ElFormItem label="强调色 (Accent)">
            <div class="color-picker-row">
              <ElColorPicker
                :model-value="form.confirmation_color_scheme.accent"
                @update:model-value="(c) => handleColorChange('accent', c)"
                show-alpha
              />
              <ElInput
                :model-value="form.confirmation_color_scheme.accent"
                @update:model-value="(c) => handleColorChange('accent', c)"
                class="color-input"
              />
            </div>
          </ElFormItem>
        </ElCol>
        <ElCol :span="12" :xs="24">
          <ElFormItem label="背景色 (Background)">
            <div class="color-picker-row">
              <ElColorPicker
                :model-value="form.confirmation_color_scheme.background"
                @update:model-value="(c) => handleColorChange('background', c)"
                show-alpha
              />
              <ElInput
                :model-value="form.confirmation_color_scheme.background"
                @update:model-value="(c) => handleColorChange('background', c)"
                class="color-input"
              />
            </div>
          </ElFormItem>
        </ElCol>
        <ElCol :span="12" :xs="24">
          <ElFormItem label="文字色 (Text)">
            <div class="color-picker-row">
              <ElColorPicker
                :model-value="form.confirmation_color_scheme.text"
                @update:model-value="(c) => handleColorChange('text', c)"
                show-alpha
              />
              <ElInput
                :model-value="form.confirmation_color_scheme.text"
                @update:model-value="(c) => handleColorChange('text', c)"
                class="color-input"
              />
            </div>
          </ElFormItem>
        </ElCol>
        <ElCol :span="12" :xs="24">
          <ElFormItem label="次文字色 (Text Secondary)">
            <div class="color-picker-row">
              <ElColorPicker
                :model-value="form.confirmation_color_scheme.text_secondary"
                @update:model-value="(c) => handleColorChange('text_secondary', c)"
                show-alpha
              />
              <ElInput
                :model-value="form.confirmation_color_scheme.text_secondary"
                @update:model-value="(c) => handleColorChange('text_secondary', c)"
                class="color-input"
              />
            </div>
          </ElFormItem>
        </ElCol>
      </ElRow>
    </ElCard>

    <!-- 6. Icon Approach -->
    <ElCard class="form-section">
      <template #header>
        <div class="section-header">
          <ElIcon :size="18" color="var(--primary-color)"><CollectionTag /></ElIcon>
          <span>6. 图标方案 (Icon Approach)</span>
        </div>
      </template>
      <ElFormItem label="图标风格" required>
        <ElSelect v-model="form.confirmation_icon_approach" class="full-width">
          <ElOption
            v-for="opt in iconApproachOptions"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          >
            <div class="select-option">
              <span>{{ opt.label }}</span>
              <span class="option-desc">{{ opt.desc }}</span>
            </div>
          </ElOption>
        </ElSelect>
      </ElFormItem>
    </ElCard>

    <!-- 7. Typography -->
    <ElCard class="form-section">
      <template #header>
        <div class="section-header">
          <ElIcon :size="18" color="var(--primary-color)"><FontSize /></ElIcon>
          <span>7. 字体配置 (Typography)</span>
        </div>
      </template>
      <ElRow :gutter="16">
        <ElCol :span="12" :xs="24">
          <ElFormItem label="标题字体" required>
            <ElSelect v-model="form.confirmation_typography.title_font" class="full-width">
              <ElOption
                v-for="font in fontOptions"
                :key="font.value"
                :label="font.label"
                :value="font.value"
              />
            </ElSelect>
          </ElFormItem>
        </ElCol>
        <ElCol :span="12" :xs="24">
          <ElFormItem label="正文字体" required>
            <ElSelect v-model="form.confirmation_typography.body_font" class="full-width">
              <ElOption
                v-for="font in fontOptions"
                :key="font.value"
                :label="font.label"
                :value="font.value"
              />
            </ElSelect>
          </ElFormItem>
        </ElCol>
      </ElRow>
    </ElCard>

    <!-- 8. Image Approach -->
    <ElCard class="form-section">
      <template #header>
        <div class="section-header">
          <ElIcon :size="18" color="var(--primary-color)"><Picture /></ElIcon>
          <span>8. 图片方案 (Image Approach)</span>
        </div>
      </template>
      <ElFormItem label="图片获取方式" required>
        <ElSelect v-model="form.confirmation_image_approach" class="full-width">
          <ElOption
            v-for="opt in imageApproachOptions"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          >
            <div class="select-option">
              <span>{{ opt.label }}</span>
              <span class="option-desc">{{ opt.desc }}</span>
            </div>
          </ElOption>
        </ElSelect>
      </ElFormItem>
    </ElCard>

    <!-- 提交按钮 -->
    <div class="form-actions">
      <ElTooltip content="提交后将开始生成页面" placement="top">
        <ElButton
          type="primary"
          size="large"
          :loading="loading"
          @click="handleSubmit"
          class="submit-btn"
        >
          <ElIcon><CircleCheck /></ElIcon>
          确认并继续
        </ElButton>
      </ElTooltip>
      <p class="submit-hint">请仔细确认以上8项配置，提交后将进入页面生成阶段</p>
    </div>
  </div>
</template>

<!-- EightConfirmationsForm.vue -->

<style scoped>
.confirmations-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-section {
  border-radius: var(--border-radius-md);
  transition: box-shadow var(--transition-base);
}

.form-section:hover {
  box-shadow: var(--shadow-md);
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.full-width {
  width: 100%;
}

.page-count-input {
  margin-right: 12px;
}

.input-hint {
  font-size: 13px;
  color: var(--text-muted);
}

.color-picker-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.color-input {
  flex: 1;
  max-width: 140px;
}

.select-option {
  display: flex;
  flex-direction: column;
  padding: 4px 0;
}

.option-desc {
  font-size: 12px;
  color: var(--text-muted);
}

.form-actions {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 24px 0 8px;
}

.submit-btn {
  min-width: 200px;
  font-size: 16px;
  border-radius: var(--border-radius-md);
}

.submit-hint {
  font-size: 13px;
  color: var(--text-muted);
  text-align: center;
}
</style>
