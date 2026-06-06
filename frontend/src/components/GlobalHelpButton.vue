<template>
  <button class="global-help-btn" title="打开帮助中心" @click="openHelp">
    <span>?</span>
    <small>帮助</small>
  </button>

  <HelpCenterModal v-if="helpOpen" @close="closeHelp" />
</template>

<script setup>
import { ref } from "vue";

import HelpCenterModal from "@/components/HelpCenterModal.vue";

const helpOpen = ref(false);

function openHelp() {
  helpOpen.value = true;
}

function closeHelp() {
  helpOpen.value = false;
}
</script>

<style scoped>
.global-help-btn {
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  gap: 0.36rem;
  border-radius: 999px;
  border: 1px solid var(--line);
  background: color-mix(in srgb, var(--card), white 14%);
  color: var(--text);
  padding: 0.48rem 0.78rem;
  box-shadow: 0 6px 14px var(--shadow);
}

.global-help-btn:hover {
  background: var(--primary-soft);
  border-color: var(--primary-soft-border);
  color: var(--primary);
  transform: translateY(-1px);
}

.global-help-btn span {
  width: 22px;
  height: 22px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  background: var(--primary);
  color: #fff;
  font-weight: 900;
  line-height: 1;
}

.global-help-btn small {
  font-weight: 800;
}

:global(html[data-theme="dark"]) .global-help-btn span {
  color: #042f2e;
  background: var(--primary);
}
</style>
