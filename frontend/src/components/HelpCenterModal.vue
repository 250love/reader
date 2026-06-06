<template>
  <Teleport to="body">
    <div class="help-backdrop" @click.self="emitClose">
      <section class="help-modal" role="dialog" aria-modal="true" aria-labelledby="help-title">
        <aside class="help-sidebar">
          <div class="help-sidebar-head">
            <p class="brand-kicker">Guide</p>
            <h2 id="help-title">帮助中心</h2>
          </div>

          <nav class="help-nav" aria-label="帮助分类">
            <button
              v-for="section in helpSections"
              :key="section.key"
              :class="{ active: activeKey === section.key }"
              @click="activeKey = section.key"
            >
              <span class="help-nav-icon">{{ section.icon }}</span>
              <span>{{ section.navLabel }}</span>
            </button>
          </nav>
        </aside>

        <main class="help-content">
          <header class="help-content-head">
            <div>
              <p class="brand-kicker">Paper Reader Lab</p>
              <h3>{{ activeSection.title }}</h3>
              <p>{{ activeSection.summary }}</p>
            </div>
            <button class="help-close" aria-label="关闭帮助中心" @click="emitClose">×</button>
          </header>

          <section class="help-scroll">
            <article
              v-for="block in activeSection.blocks"
              :key="`${activeSection.key}-${block.heading}`"
              :class="['help-block', block.kind ? `help-block-${block.kind}` : '']"
            >
              <h4>{{ block.heading }}</h4>
              <p v-if="block.text">{{ block.text }}</p>
              <ol v-if="block.items?.length">
                <li v-for="item in block.items" :key="item">{{ item }}</li>
              </ol>
            </article>
          </section>
        </main>
      </section>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

import { helpSections } from "@/data/helpContent";

const emit = defineEmits(["close"]);

const activeKey = ref(helpSections[0]?.key || "");
let previousBodyOverflow = "";
const activeSection = computed(() => helpSections.find((section) => section.key === activeKey.value) || helpSections[0]);

function emitClose() {
  emit("close");
}

function handleKeydown(event) {
  if (event.key === "Escape") {
    emitClose();
  }
}

onMounted(() => {
  previousBodyOverflow = document.body.style.overflow;
  document.body.style.overflow = "hidden";
  window.addEventListener("keydown", handleKeydown);
});

onBeforeUnmount(() => {
  document.body.style.overflow = previousBodyOverflow;
  window.removeEventListener("keydown", handleKeydown);
});
</script>

<style scoped>
.help-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1600;
  display: grid;
  place-items: center;
  padding: 1rem;
  background: rgba(5, 12, 22, 0.58);
  backdrop-filter: blur(4px);
}

.help-modal {
  width: min(1080px, 94vw);
  height: min(86vh, 820px);
  max-height: 86vh;
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: 24px;
  background: linear-gradient(180deg, var(--surface) 0%, var(--surface-soft) 100%);
  color: var(--text);
  box-shadow: 0 28px 70px var(--shadow);
}

.help-sidebar {
  min-height: 0;
  border-right: 1px solid var(--line);
  background: color-mix(in srgb, var(--surface-soft), var(--bg) 28%);
  padding: 0.85rem;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 0.78rem;
}

.help-sidebar-head h2,
.help-content-head h3 {
  margin: 0.2rem 0 0;
  font-family: "Space Grotesk", "IBM Plex Sans", sans-serif;
}

.help-sidebar-head h2 {
  font-size: 1.4rem;
}

.help-nav {
  min-height: 0;
  overflow-y: auto;
  scrollbar-gutter: stable;
  display: grid;
  align-content: start;
  gap: 0.28rem;
  padding-right: 0.1rem;
}

.help-nav button {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 0.55rem;
  border: 1px solid transparent;
  border-radius: 14px;
  background: transparent;
  color: var(--text);
  padding: 0.56rem 0.62rem;
  text-align: left;
  font-weight: 700;
}

.help-nav button:hover {
  background: var(--surface-muted);
  border-color: var(--line);
}

.help-nav button.active {
  background: var(--primary-soft);
  border-color: var(--primary-soft-border);
  color: var(--primary);
}

.help-nav-icon {
  width: 28px;
  height: 28px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  background: color-mix(in srgb, var(--primary-soft), var(--surface) 42%);
  color: var(--primary);
  font-size: 0.8rem;
  font-weight: 900;
  letter-spacing: 0.02em;
}

.help-content {
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
}

.help-content-head {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-start;
  padding: 1.1rem 1.2rem 0.95rem;
  border-bottom: 1px solid var(--line);
}

.help-content-head p {
  max-width: 680px;
  margin: 0.35rem 0 0;
  color: var(--muted);
  line-height: 1.55;
}

.help-close {
  width: 42px;
  height: 42px;
  flex: 0 0 auto;
  border-radius: 14px;
  padding: 0;
  border: 1px solid var(--line);
  background: var(--surface);
  color: var(--text);
  font-size: 1.45rem;
  line-height: 1;
  box-shadow: 0 8px 18px var(--shadow);
}

.help-close:hover {
  background: var(--danger-soft);
  border-color: color-mix(in srgb, var(--danger), var(--line) 45%);
  color: var(--danger);
}

.help-scroll {
  min-height: 0;
  overflow-y: auto;
  scrollbar-gutter: stable;
  padding: 1rem 1.2rem 1.25rem;
  display: grid;
  align-content: start;
  gap: 0.82rem;
}

.help-nav,
.help-scroll {
  scrollbar-width: thin;
  scrollbar-color: color-mix(in srgb, var(--primary), var(--muted) 55%) color-mix(in srgb, var(--surface-muted), transparent 20%);
}

.help-nav::-webkit-scrollbar,
.help-scroll::-webkit-scrollbar {
  width: 10px;
  height: 10px;
}

.help-nav::-webkit-scrollbar-track,
.help-scroll::-webkit-scrollbar-track {
  background: color-mix(in srgb, var(--surface-muted), transparent 18%);
  border-radius: 999px;
}

.help-nav::-webkit-scrollbar-thumb,
.help-scroll::-webkit-scrollbar-thumb {
  min-height: 48px;
  border: 2px solid color-mix(in srgb, var(--surface), transparent 15%);
  border-radius: 999px;
  background: color-mix(in srgb, var(--primary), var(--muted) 55%);
}

.help-nav::-webkit-scrollbar-thumb:hover,
.help-scroll::-webkit-scrollbar-thumb:hover {
  background: var(--primary);
}

.help-block {
  border: 1px solid var(--line);
  border-radius: 18px;
  background: var(--surface);
  padding: 0.95rem;
  box-shadow: 0 8px 22px var(--shadow);
}

.help-block h4 {
  margin: 0;
  font-family: "Space Grotesk", "IBM Plex Sans", sans-serif;
}

.help-block p {
  margin: 0.45rem 0 0;
  color: var(--muted);
  line-height: 1.68;
}

.help-block ol {
  margin: 0.58rem 0 0;
  padding-left: 1.25rem;
  color: var(--text);
  line-height: 1.72;
}

.help-block li + li {
  margin-top: 0.22rem;
}

.help-block-tip {
  background: color-mix(in srgb, var(--primary-soft), var(--surface) 72%);
  border-color: var(--primary-soft-border);
}

.help-block-warning {
  background: color-mix(in srgb, var(--danger-soft), var(--surface) 62%);
  border-color: color-mix(in srgb, var(--danger), var(--line) 62%);
}

:global(html[data-theme="dark"]) .help-backdrop {
  background: rgba(2, 6, 23, 0.68);
}

:global(html[data-theme="dark"]) .help-modal {
  background: linear-gradient(180deg, var(--surface) 0%, #0b1220 100%);
  border-color: rgba(203, 213, 225, 0.28);
}

:global(html[data-theme="dark"]) .help-sidebar {
  background: linear-gradient(180deg, #121b2c 0%, #0b1220 100%);
  border-color: rgba(203, 213, 225, 0.24);
}

:global(html[data-theme="dark"]) .help-nav button:hover {
  background: rgba(226, 232, 240, 0.08);
  border-color: rgba(226, 232, 240, 0.18);
}

:global(html[data-theme="dark"]) .help-nav button.active {
  background: rgba(94, 234, 212, 0.16);
  border-color: rgba(94, 234, 212, 0.38);
  color: #7ffbea;
}

:global(html[data-theme="dark"]) .help-block,
:global(html[data-theme="dark"]) .help-close {
  background: #0f1c2f;
  border-color: rgba(203, 213, 225, 0.28);
}

:global(html[data-theme="dark"]) .help-block-tip {
  background: rgba(45, 212, 191, 0.13);
  border-color: rgba(94, 234, 212, 0.34);
}

:global(html[data-theme="dark"]) .help-block-warning {
  background: rgba(248, 113, 113, 0.12);
  border-color: rgba(252, 165, 165, 0.34);
}

:global(html[data-theme="dark"]) .help-nav,
:global(html[data-theme="dark"]) .help-scroll {
  scrollbar-color: rgba(94, 234, 212, 0.72) rgba(226, 232, 240, 0.08);
}

:global(html[data-theme="dark"]) .help-nav::-webkit-scrollbar-track,
:global(html[data-theme="dark"]) .help-scroll::-webkit-scrollbar-track {
  background: rgba(226, 232, 240, 0.08);
}

:global(html[data-theme="dark"]) .help-nav::-webkit-scrollbar-thumb,
:global(html[data-theme="dark"]) .help-scroll::-webkit-scrollbar-thumb {
  border-color: #0f1c2f;
  background: rgba(94, 234, 212, 0.72);
}

:global(html[data-theme="dark"]) .help-nav::-webkit-scrollbar-thumb:hover,
:global(html[data-theme="dark"]) .help-scroll::-webkit-scrollbar-thumb:hover {
  background: #99f6e4;
}

@media (max-width: 760px) {
  .help-modal {
    grid-template-columns: 1fr;
    height: min(88vh, 820px);
    max-height: 88vh;
  }

  .help-sidebar {
    grid-template-rows: auto auto;
    border-right: 0;
    border-bottom: 1px solid var(--line);
  }

  .help-nav {
    display: flex;
    overflow-x: auto;
    overflow-y: hidden;
    padding-bottom: 0.2rem;
  }

  .help-nav button {
    min-width: 138px;
  }

  .help-content-head {
    padding: 0.9rem;
  }

  .help-scroll {
    padding: 0.9rem;
  }
}
</style>
