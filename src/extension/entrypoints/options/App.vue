<template>
  <main class="if-options">
    <h1 class="if-options__title">{{ title }}</h1>

    <label class="if-options__row">
      <input type="checkbox" :checked="autoEnter" @change="onToggle" />
      <span class="if-options__label">{{ label }}</span>
    </label>

    <p class="if-options__hint">{{ hint }}</p>
  </main>
</template>

<script lang="ts" setup>
import { onMounted, ref } from 'vue';
import { getOptions, saveOptions } from '@/lib/storage';

const autoEnter = ref(false);

function t(key: string, fallback: string): string {
  try {
    const extensionGlobal = globalThis as typeof globalThis & {
      chrome?: { i18n?: { getMessage?: (name: string) => string } };
    };
    return extensionGlobal.chrome?.i18n?.getMessage?.(key) || fallback;
  } catch {
    return fallback;
  }
}

const title = t('optionsTitle', 'InsightFlow Settings');
const label = t('autoEnterReadingModeLabel', 'Automatically enter deep reading mode on page load');
const hint = t(
  'autoEnterReadingModeHint',
  'When on, article pages automatically open in full-screen deep reading after they load.',
);

onMounted(async () => {
  const options = await getOptions();
  autoEnter.value = options.autoEnterReadingMode;
});

async function onToggle(event: Event): Promise<void> {
  const checked = (event.target as HTMLInputElement).checked;
  autoEnter.value = checked;
  await saveOptions({ autoEnterReadingMode: checked });
}
</script>

<style scoped>
.if-options {
  max-width: 640px;
  margin: 0 auto;
  padding: 32px 24px;
  font-family: system-ui, -apple-system, 'Segoe UI', 'Microsoft YaHei', sans-serif;
  color: #1f1f1f;
}
.if-options__title {
  margin: 0 0 24px;
  font-size: 20px;
  font-weight: 700;
}
.if-options__row {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
}
.if-options__row input {
  width: 18px;
  height: 18px;
  cursor: pointer;
  accent-color: #43bf4f;
}
.if-options__label {
  font-size: 15px;
  font-weight: 600;
}
.if-options__hint {
  margin: 12px 0 0 28px;
  color: #666;
  font-size: 13px;
  line-height: 1.6;
}
</style>
