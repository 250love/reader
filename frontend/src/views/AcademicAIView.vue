<template>
  <section class="ai-workbench">
    <aside class="tool-rail">
      <button class="rail-action primary" title="新对话" @click="startNewChat">
        <span>新</span>
        <small>新对话</small>
      </button>

      <nav class="rail-nav">
        <button
          v-for="item in railItems"
          :key="item.key"
          :class="{ active: activeDrawer === item.key && !drawerCollapsed }"
          :title="item.label"
          @click="openDrawer(item.key)"
        >
          <span>{{ item.short }}</span>
          <small>{{ item.label }}</small>
        </button>

        <div class="more-wrap">
          <button :class="{ active: moreMenuOpen }" title="更多工具" @click.stop="toggleMoreMenu">
            <span>...</span>
            <small>更多</small>
          </button>

          <section v-if="moreMenuOpen" class="more-menu" @click.stop>
            <button v-for="item in moreTools" :key="item.key" :disabled="item.disabled" @click="onMoreTool(item)">
              <span>{{ item.label }}</span>
              <small>{{ item.disabled ? "后续开放" : item.hint }}</small>
            </button>
          </section>
        </div>
      </nav>
    </aside>

    <aside v-if="!drawerCollapsed" class="context-drawer">
      <header class="drawer-head">
        <div>
          <p class="brand-kicker">Workspace Tools</p>
          <h3>{{ activeDrawerTitle }}</h3>
        </div>
        <button class="drawer-close" title="收起工具栏" @click="drawerCollapsed = true">×</button>
      </header>

      <section v-if="activeDrawer === 'context'" class="drawer-section">
        <div class="section-title-row">
          <div>
            <h4>论文上下文</h4>
            <p>{{ selectedPaperIds.length }} / {{ papers.length }} 篇已选择</p>
          </div>
          <button class="btn-secondary small-btn" :disabled="selectedPaperIds.length === 0" @click="clearSelection">
            清空
          </button>
        </div>

        <input v-model="paperSearch" class="soft-input" placeholder="搜索标题、作者、来源或年份" />

        <p v-if="loadingData" class="muted-text">正在加载文献...</p>
        <p v-else-if="dataError" class="error-text">{{ dataError }}</p>
        <p v-else-if="papers.length === 0" class="muted-text">暂无文献，请先在论文管理中导入 PDF。</p>
        <p v-else-if="filteredPapers.length === 0" class="muted-text">没有匹配的论文。</p>

        <div v-else class="paper-list compact-scroll">
          <label
            v-for="paper in filteredPapers"
            :key="paper.id"
            :class="['paper-option', { selected: selectedIdSet.has(paper.id) }]"
          >
            <input type="checkbox" :checked="selectedIdSet.has(paper.id)" @change="togglePaper(paper.id)" />
            <span>
              <strong>{{ paper.title || "Untitled" }}</strong>
              <em>{{ paper.authors || "未知作者" }}</em>
              <small>{{ paper.conference || "未填写来源" }} · {{ paper.year || "n.d." }}</small>
            </span>
          </label>
        </div>

        <div class="context-options">
          <h4>上下文范围</h4>
          <label><input v-model="contextOptions.include_metadata" type="checkbox" /> 文献信息</label>
          <label><input v-model="contextOptions.include_pdf_excerpt" type="checkbox" /> PDF 摘要内容</label>
          <label><input v-model="contextOptions.include_annotations" type="checkbox" /> 我的高亮笔记</label>
          <label><input v-model="contextOptions.include_figures" type="checkbox" /> 图表说明</label>
        </div>
      </section>

      <section v-else-if="activeDrawer === 'tasks'" class="drawer-section">
        <div class="section-title-row">
          <div>
            <h4>快捷任务</h4>
            <p>选择论文后可直接运行。</p>
          </div>
        </div>

        <div class="task-list">
          <button
            v-for="task in normalTasks"
            :key="task.key"
            :class="{ active: selectedTask === task.key }"
            :disabled="loading"
            @click="runTask(task.key)"
          >
            <strong>{{ task.label }}</strong>
            <span>{{ task.description }}</span>
          </button>
        </div>
      </section>

      <section v-else-if="activeDrawer === 'model'" class="drawer-section">
        <div class="section-title-row">
          <div>
            <h4>模型设置</h4>
            <p>复用账号设置中的 LLM Provider。</p>
          </div>
        </div>

        <label class="field-label">
          Provider
          <select v-model="selectedProviderId" :disabled="providers.length === 0">
            <option value="">默认 Provider</option>
            <option v-for="provider in providers" :key="provider.id" :value="provider.id">
              {{ provider.name }} / {{ provider.model }}{{ provider.is_default ? "（默认）" : "" }}
            </option>
          </select>
        </label>

        <label class="field-label">
          输出语言
          <select v-model="targetLang">
            <option value="zh-CN">中文</option>
            <option value="en">English</option>
          </select>
        </label>

        <p v-if="providers.length === 0" class="warning-text">
          请先到账号设置中配置 LLM Provider，否则无法生成回答。
        </p>
      </section>

      <section v-else class="drawer-section">
        <div class="section-title-row">
          <div>
            <h4>历史结果</h4>
            <p>Phase 5 将在这里显示最近生成记录。</p>
          </div>
        </div>

        <div class="placeholder-card">
          <strong>历史记录预留区</strong>
          <p>后续接入 `ai_runs` 后，可在这里回看、删除和恢复历史回答。</p>
        </div>
      </section>
    </aside>

    <main class="chat-shell">
      <header class="chat-topbar">
        <div>
          <p class="brand-kicker">Academic AI</p>
          <h2>学术 AI 工作台</h2>
        </div>
        <div class="topbar-actions">
          <button v-if="drawerCollapsed" class="btn-secondary" @click="drawerCollapsed = false">展开工具栏</button>
          <button class="btn-secondary" :disabled="loadingData" @click="loadInitialData">
            {{ loadingData ? "刷新中..." : "刷新数据" }}
          </button>
          <button class="btn-secondary" :disabled="messages.length === 0 && !noticeMessage" @click="clearConversation">
            清空对话
          </button>
        </div>
      </header>

      <section ref="messageListRef" class="message-list">
        <div v-if="messages.length === 0" class="empty-state">
          <p class="brand-kicker">Start With Your Papers</p>
          <h3>学术 AI 助手</h3>
          <p>选择论文后，可以让 AI 帮你完成论文速读、方法拆解、多篇对比和汇报准备。</p>

          <div class="suggestion-grid">
            <button v-for="task in normalTasks" :key="task.key" @click="runTask(task.key)">
              <strong>{{ task.label }}</strong>
              <span>{{ task.description }}</span>
            </button>
          </div>
        </div>

        <article
          v-for="message in messages"
          :key="message.id"
          :class="['message-row', message.role, { loading: message.loading, error: message.error }]"
        >
          <div class="message-bubble">
            <header class="message-meta">
              <span>{{ message.role === "user" ? "你" : "学术 AI" }}</span>
              <small>{{ message.label }}</small>
            </header>

            <p v-if="message.loading" class="loading-text">正在生成回答...</p>
            <p v-else-if="message.error" class="error-text">{{ message.content }}</p>
            <pre v-else>{{ message.content }}</pre>

            <footer v-if="message.role === 'assistant' && !message.loading" class="message-actions">
              <button class="btn-secondary" @click="copyMessage(message)" :disabled="message.error">复制 Markdown</button>
              <button
                v-if="message.sources?.length"
                class="btn-secondary"
                @click="message.expandedSources = !message.expandedSources"
              >
                {{ message.expandedSources ? "收起来源" : "展开来源" }}
              </button>
              <button v-if="message.payload" class="btn-secondary" :disabled="loading" @click="regenerate(message)">
                重新生成
              </button>
            </footer>

            <section v-if="message.expandedSources" class="source-panel">
              <div v-for="source in message.sources" :key="source.paper_id" class="source-item">
                <strong>{{ source.title }}</strong>
                <span>PDF 摘录：{{ source.has_pdf_excerpt ? `第 ${source.pages.join(", ")} 页` : "未使用" }}</span>
                <span>笔记 {{ source.used_annotations }} 条 · 图表说明 {{ source.used_figures }} 条</span>
              </div>
            </section>

            <section v-if="message.suggestedQuestions?.length" class="followup-row">
              <button
                v-for="question in message.suggestedQuestions"
                :key="question"
                class="btn-secondary"
                @click="customQuery = question"
              >
                {{ question }}
              </button>
            </section>
          </div>
        </article>
      </section>

      <footer class="composer-wrap">
        <p v-if="noticeMessage" class="notice-text">{{ noticeMessage }}</p>
        <div class="composer-summary">
          <span>{{ selectedPaperIds.length }} 篇论文</span>
          <span>{{ contextSummary }}</span>
          <span>{{ providerSummary }}</span>
        </div>
        <div class="composer-box">
          <textarea
            v-model="customQuery"
            rows="1"
            placeholder="输入你想问的问题，例如：这篇论文适合怎么汇报？"
            @keydown.enter.exact.prevent="runTask('custom_qa')"
          />
          <button :disabled="loading" @click="runTask('custom_qa')">发送</button>
        </div>
      </footer>
    </main>
  </section>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import {
  fetchAgentTasks,
  fetchPapers,
  fetchProviders,
  runAcademicAgent
} from "@/services/api";

const route = useRoute();
const router = useRouter();

const papers = ref([]);
const providers = ref([]);
const tasks = ref([]);
const selectedPaperIds = ref([]);
const selectedTask = ref("paper_summary");
const selectedProviderId = ref("");
const targetLang = ref("zh-CN");
const customQuery = ref("");
const paperSearch = ref("");
const loadingData = ref(false);
const loading = ref(false);
const dataError = ref("");
const noticeMessage = ref("");
const messages = ref([]);
const activeDrawer = ref("context");
const drawerCollapsed = ref(false);
const moreMenuOpen = ref(false);
const messageListRef = ref(null);

const contextOptions = reactive({
  include_metadata: true,
  include_pdf_excerpt: true,
  include_annotations: true,
  include_figures: true
});

const railItems = [
  { key: "context", label: "上下文", short: "文" },
  { key: "tasks", label: "任务", short: "任" },
  { key: "model", label: "模型", short: "模" },
  { key: "history", label: "历史", short: "史" }
];

const moreTools = [
  { key: "dashboard", label: "论文管理", hint: "打开文献库", routeName: "dashboard" },
  { key: "citations", label: "引用助手", hint: "打开引用页", routeName: "citations" },
  { key: "fulltext", label: "全文搜索", disabled: true },
  { key: "figures", label: "图表与表格", disabled: true },
  { key: "essay", label: "随笔", disabled: true },
  { key: "plan", label: "阅读计划", disabled: true },
  { key: "theme", label: "主题设置", disabled: true },
  { key: "help", label: "帮助", disabled: true }
];

const selectedIdSet = computed(() => new Set(selectedPaperIds.value));

const filteredPapers = computed(() => {
  const keyword = paperSearch.value.trim().toLowerCase();
  if (!keyword) return papers.value;
  return papers.value.filter((paper) => {
    const haystack = [
      paper.title,
      paper.authors,
      paper.conference,
      paper.year,
      Array.isArray(paper.tags) ? paper.tags.join(" ") : ""
    ].join(" ").toLowerCase();
    return haystack.includes(keyword);
  });
});

const normalTasks = computed(() => tasks.value.filter((task) => task.key !== "custom_qa"));

const selectedTaskMeta = computed(() => tasks.value.find((task) => task.key === selectedTask.value));

const activeDrawerTitle = computed(() => {
  const item = railItems.find((entry) => entry.key === activeDrawer.value);
  return item?.label || "工具";
});

const activeProvider = computed(() => {
  if (selectedProviderId.value) {
    return providers.value.find((provider) => provider.id === selectedProviderId.value);
  }
  return providers.value.find((provider) => provider.is_default) || providers.value[0];
});

const providerSummary = computed(() => {
  if (!providers.value.length) return "未配置 Provider";
  if (!activeProvider.value) return "默认 Provider";
  return `${activeProvider.value.name} / ${activeProvider.value.model}`;
});

const contextSummary = computed(() => {
  const enabled = [];
  if (contextOptions.include_metadata) enabled.push("文献信息");
  if (contextOptions.include_pdf_excerpt) enabled.push("PDF 摘要");
  if (contextOptions.include_annotations) enabled.push("高亮笔记");
  if (contextOptions.include_figures) enabled.push("图表说明");
  return enabled.length ? `上下文：${enabled.join(" / ")}` : "未启用上下文";
});

async function loadInitialData() {
  loadingData.value = true;
  dataError.value = "";
  noticeMessage.value = "";
  try {
    const [paperRows, providerRows, taskRows] = await Promise.all([
      fetchPapers({ sort_by: "last_opened_at", sort_order: "desc" }),
      fetchProviders(),
      fetchAgentTasks()
    ]);
    papers.value = paperRows;
    providers.value = providerRows;
    tasks.value = taskRows;
    applyQueryDefaults();
  } catch (error) {
    dataError.value = error?.response?.data?.error || "学术 AI 数据加载失败，请稍后重试。";
  } finally {
    loadingData.value = false;
  }
}

function applyQueryDefaults() {
  const paperId = String(route.query.paper_id || "").trim();
  const task = String(route.query.task || "").trim();
  if (paperId && papers.value.some((paper) => paper.id === paperId)) {
    selectedPaperIds.value = [paperId];
  }
  if (task && tasks.value.some((item) => item.key === task)) {
    selectedTask.value = task;
  }
}

function openDrawer(key) {
  activeDrawer.value = key;
  drawerCollapsed.value = false;
  moreMenuOpen.value = false;
}

function toggleMoreMenu() {
  moreMenuOpen.value = !moreMenuOpen.value;
}

function onMoreTool(item) {
  if (item.disabled) {
    noticeMessage.value = `${item.label} 将在后续版本开放。`;
    moreMenuOpen.value = false;
    return;
  }
  if (item.routeName) {
    router.push({ name: item.routeName });
  }
}

function togglePaper(paperId) {
  if (selectedIdSet.value.has(paperId)) {
    selectedPaperIds.value = selectedPaperIds.value.filter((id) => id !== paperId);
    return;
  }
  selectedPaperIds.value = [...selectedPaperIds.value, paperId];
}

function clearSelection() {
  selectedPaperIds.value = [];
}

function validateBeforeRun(taskKey, queryText = customQuery.value) {
  const count = selectedPaperIds.value.length;
  const task = tasks.value.find((item) => item.key === taskKey);
  if (!task) return "任务模板不存在。";
  if (!providers.value.length) return "请先到账号设置中配置 LLM Provider。";
  if (task.mode === "single" && count !== 1) return "该任务需要选择 1 篇论文。";
  if (task.mode === "multi" && (count < 2 || count > 3)) return "多篇对比需要选择 2-3 篇论文。";
  if (task.mode === "single_or_multi" && (count < 1 || count > 3)) return "自定义提问需要选择 1-3 篇论文。";
  if (taskKey === "custom_qa" && !queryText.trim()) return "请输入自定义问题。";
  return "";
}

function buildUserPrompt(taskKey, queryText) {
  const task = tasks.value.find((item) => item.key === taskKey);
  if (taskKey === "custom_qa") return queryText.trim();
  return `请基于已选论文执行「${task?.label || taskKey}」。`;
}

function makeMessage(role, data) {
  return {
    id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    role,
    label: "",
    content: "",
    loading: false,
    error: false,
    sources: [],
    suggestedQuestions: [],
    expandedSources: false,
    payload: null,
    ...data
  };
}

async function runTask(taskKey, options = {}) {
  selectedTask.value = taskKey;
  noticeMessage.value = "";
  const queryText = options.queryOverride ?? customQuery.value;
  const validationError = validateBeforeRun(taskKey, queryText);
  if (validationError) {
    noticeMessage.value = validationError;
    if (validationError.includes("论文")) openDrawer("context");
    if (validationError.includes("Provider")) openDrawer("model");
    return;
  }

  const task = tasks.value.find((item) => item.key === taskKey);
  const payload = {
    task: taskKey,
    paper_ids: [...selectedPaperIds.value],
    query: queryText,
    provider_id: selectedProviderId.value || undefined,
    target_lang: targetLang.value,
    context_options: { ...contextOptions }
  };

  const userMessage = makeMessage("user", {
    label: task?.label || "自定义提问",
    content: options.regenerate ? `重新生成：${buildUserPrompt(taskKey, queryText)}` : buildUserPrompt(taskKey, queryText)
  });
  const assistantMessage = makeMessage("assistant", {
    label: task?.label || "学术 AI",
    content: "正在生成回答...",
    loading: true,
    payload
  });

  messages.value.push(userMessage, assistantMessage);
  loading.value = true;
  await scrollToBottom();

  try {
    const result = await runAcademicAgent(payload);
    Object.assign(assistantMessage, {
      content: result.answer || "",
      loading: false,
      sources: result.sources || [],
      suggestedQuestions: result.suggested_questions || [],
      payload
    });
  } catch (error) {
    Object.assign(assistantMessage, {
      content: error?.response?.data?.error || "学术 AI 调用失败",
      loading: false,
      error: true,
      payload
    });
  } finally {
    loading.value = false;
    await scrollToBottom();
  }
}

async function scrollToBottom() {
  await nextTick();
  const el = messageListRef.value;
  if (el) {
    el.scrollTop = el.scrollHeight;
  }
}

async function copyMessage(message) {
  if (!message?.content || message.error) return;
  try {
    await navigator.clipboard.writeText(message.content);
    noticeMessage.value = "Markdown 已复制到剪贴板。";
  } catch {
    noticeMessage.value = "复制失败，请手动选择文本复制。";
  }
}

function regenerate(message) {
  if (!message?.payload) return;
  customQuery.value = message.payload.query || customQuery.value;
  runTask(message.payload.task, {
    queryOverride: message.payload.query || "",
    regenerate: true
  });
}

function clearConversation() {
  messages.value = [];
  noticeMessage.value = "";
}

function startNewChat() {
  clearConversation();
  customQuery.value = "";
  activeDrawer.value = "context";
  drawerCollapsed.value = false;
}

onMounted(loadInitialData);
</script>

<style scoped>
.ai-workbench {
  min-height: calc(100vh - 150px);
  display: grid;
  grid-template-columns: 82px minmax(280px, 360px) minmax(0, 1fr);
  gap: 0.75rem;
}

.tool-rail,
.context-drawer,
.chat-shell {
  border: 1px solid rgba(153, 168, 180, 0.45);
  background: color-mix(in srgb, var(--card), white 24%);
  box-shadow: 0 10px 26px rgba(38, 55, 72, 0.08);
}

.tool-rail {
  position: relative;
  border-radius: 22px;
  padding: 0.65rem 0.42rem;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 0.7rem;
}

.rail-nav {
  display: grid;
  gap: 0.45rem;
}

.tool-rail button,
.task-list button,
.suggestion-grid button {
  border-color: transparent;
}

.tool-rail button {
  width: 100%;
  min-height: 58px;
  border-radius: 16px;
  background: transparent;
  color: #344a5c;
  display: grid;
  justify-items: center;
  gap: 0.15rem;
  padding: 0.45rem 0.2rem;
}

.tool-rail button:hover,
.tool-rail button.active {
  background: #e1f0ec;
  color: #0f574f;
}

.tool-rail button.primary {
  background: var(--primary);
  color: #fff;
}

.tool-rail span {
  font-weight: 800;
  font-size: 0.96rem;
}

.tool-rail small {
  font-size: 0.7rem;
}

.more-wrap {
  position: relative;
}

.more-menu {
  position: absolute;
  left: calc(100% + 0.55rem);
  bottom: 0;
  z-index: 30;
  width: 220px;
  border: 1px solid #d2dde6;
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 18px 42px rgba(20, 36, 50, 0.18);
  padding: 0.45rem;
}

.more-menu button {
  min-height: auto;
  display: grid;
  justify-items: start;
  gap: 0.08rem;
  border-radius: 12px;
  padding: 0.55rem 0.65rem;
  text-align: left;
}

.more-menu button:disabled {
  opacity: 0.55;
}

.context-drawer {
  border-radius: 22px;
  padding: 0.9rem;
  min-height: 0;
  overflow: hidden;
}

.drawer-head,
.section-title-row,
.chat-topbar,
.topbar-actions,
.message-actions,
.followup-row,
.composer-summary {
  display: flex;
  gap: 0.6rem;
}

.drawer-head,
.section-title-row,
.chat-topbar {
  justify-content: space-between;
  align-items: flex-start;
}

.drawer-head {
  border-bottom: 1px solid #d8e2ea;
  padding-bottom: 0.72rem;
  margin-bottom: 0.85rem;
}

.drawer-head h3,
.chat-topbar h2,
.empty-state h3 {
  margin: 0.2rem 0 0;
  font-family: "Space Grotesk", sans-serif;
}

.drawer-close {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  padding: 0;
  background: #fff;
  color: #344a5c;
  border-color: #cbd8e1;
}

.drawer-section {
  display: grid;
  gap: 0.75rem;
}

.section-title-row h4,
.context-options h4 {
  margin: 0;
}

.section-title-row p {
  margin: 0.2rem 0 0;
  color: #64798a;
  font-size: 0.88rem;
}

.small-btn {
  padding: 0.32rem 0.58rem;
  border-radius: 9px;
}

.soft-input,
.field-label select {
  width: 100%;
  border: 1px solid #cbd9e4;
  border-radius: 12px;
  padding: 0.56rem 0.68rem;
  font: inherit;
  background: #fff;
}

.compact-scroll {
  max-height: 42vh;
  overflow-y: auto;
}

.paper-list,
.task-list {
  display: grid;
  gap: 0.52rem;
}

.paper-option {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 0.56rem;
  border: 1px solid #d5e0e8;
  border-radius: 14px;
  background: #fff;
  padding: 0.62rem;
  cursor: pointer;
}

.paper-option.selected {
  border-color: #0f6d64;
  background: #eefbf7;
}

.paper-option input {
  width: 18px;
  height: 18px;
  margin-top: 0.15rem;
}

.paper-option strong,
.paper-option em,
.paper-option small {
  display: block;
}

.paper-option strong {
  color: #1f3445;
  line-height: 1.35;
}

.paper-option em,
.paper-option small {
  color: #627789;
  font-size: 0.84rem;
  font-style: normal;
  margin-top: 0.16rem;
}

.context-options {
  border-top: 1px solid #d8e2ea;
  padding-top: 0.75rem;
  display: grid;
  gap: 0.45rem;
}

.context-options label {
  border: 1px solid #d5e0e8;
  border-radius: 12px;
  background: #fff;
  padding: 0.5rem 0.58rem;
  color: #30485a;
}

.task-list button {
  text-align: left;
  display: grid;
  gap: 0.22rem;
  border-radius: 14px;
  background: #fff;
  color: #23394b;
  border: 1px solid #d5e0e8;
  padding: 0.7rem;
}

.task-list button:hover,
.task-list button.active {
  background: #e9f6f2;
  border-color: #b7ded1;
}

.task-list span {
  color: #607789;
  font-size: 0.86rem;
}

.field-label {
  display: grid;
  gap: 0.35rem;
  color: #33495a;
  font-size: 0.92rem;
  font-weight: 700;
}

.placeholder-card,
.warning-text,
.notice-text {
  border-radius: 14px;
  padding: 0.75rem;
}

.placeholder-card {
  border: 1px dashed #cbd9e4;
  background: #fbfdff;
}

.placeholder-card p,
.muted-text {
  margin: 0.25rem 0 0;
  color: #627789;
}

.warning-text {
  margin: 0;
  color: #8a5a20;
  background: #fff4d8;
  border: 1px solid #efd79a;
}

.notice-text {
  margin: 0;
  color: #145c50;
  background: #e5f7f0;
  border: 1px solid #b8e5d7;
}

.error-text {
  margin: 0;
  color: #9f3a3a;
}

.chat-shell {
  min-width: 0;
  border-radius: 24px;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  overflow: hidden;
  background:
    radial-gradient(circle at 18% 0%, rgba(209, 236, 230, 0.62), transparent 28%),
    color-mix(in srgb, var(--card), white 30%);
}

.chat-topbar {
  padding: 0.95rem 1rem 0.75rem;
  border-bottom: 1px solid rgba(200, 214, 224, 0.75);
}

.topbar-actions {
  flex-wrap: wrap;
  justify-content: flex-end;
}

.message-list {
  min-height: 0;
  overflow-y: auto;
  padding: 1.1rem clamp(1rem, 3vw, 3rem);
}

.empty-state {
  min-height: 52vh;
  display: grid;
  align-content: center;
  justify-items: center;
  text-align: center;
  gap: 0.55rem;
}

.empty-state p {
  max-width: 620px;
  margin: 0;
  color: #526b7f;
}

.suggestion-grid {
  width: min(760px, 100%);
  margin-top: 1rem;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.7rem;
}

.suggestion-grid button {
  min-height: 92px;
  text-align: left;
  display: grid;
  align-content: start;
  gap: 0.3rem;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.88);
  color: #23394b;
  border: 1px solid #d7e1e8;
  padding: 0.86rem;
}

.suggestion-grid button:hover {
  background: #eef8f4;
  border-color: #b8dfd2;
}

.suggestion-grid span {
  color: #607789;
  font-size: 0.9rem;
}

.message-row {
  display: flex;
  margin: 0.78rem 0;
}

.message-row.user {
  justify-content: flex-end;
}

.message-row.assistant {
  justify-content: flex-start;
}

.message-bubble {
  width: min(840px, 92%);
  border-radius: 20px;
  padding: 0.82rem 0.92rem;
  box-shadow: 0 8px 20px rgba(30, 46, 62, 0.07);
}

.message-row.user .message-bubble {
  width: fit-content;
  max-width: min(680px, 88%);
  background: #0f6d64;
  color: #fff;
}

.message-row.assistant .message-bubble {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(206, 219, 228, 0.9);
}

.message-meta {
  display: flex;
  justify-content: space-between;
  gap: 0.8rem;
  margin-bottom: 0.45rem;
  font-size: 0.86rem;
  color: #617789;
}

.message-row.user .message-meta {
  color: rgba(255, 255, 255, 0.76);
}

.message-meta span {
  font-weight: 800;
}

.message-bubble pre,
.message-bubble p {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.68;
  font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
}

.loading-text {
  color: #145c50;
}

.message-actions {
  margin-top: 0.72rem;
  flex-wrap: wrap;
}

.message-actions button,
.followup-row button {
  border-radius: 999px;
  padding: 0.34rem 0.68rem;
  font-size: 0.84rem;
}

.source-panel {
  margin-top: 0.75rem;
  display: grid;
  gap: 0.48rem;
}

.source-item {
  display: grid;
  gap: 0.16rem;
  border: 1px solid #d4dee7;
  border-radius: 12px;
  background: #fbfdff;
  padding: 0.62rem;
}

.source-item span {
  color: #526b7f;
  font-size: 0.9rem;
}

.followup-row {
  margin-top: 0.65rem;
  flex-wrap: wrap;
}

.composer-wrap {
  position: sticky;
  bottom: 0;
  padding: 0.85rem clamp(1rem, 3vw, 3rem) 1rem;
  background: linear-gradient(180deg, rgba(255, 250, 242, 0.72), rgba(255, 250, 242, 0.98) 32%);
  border-top: 1px solid rgba(210, 222, 230, 0.78);
}

.composer-summary {
  flex-wrap: wrap;
  margin-bottom: 0.5rem;
  color: #607789;
  font-size: 0.88rem;
}

.composer-summary span {
  border: 1px solid #d7e1e8;
  background: rgba(255, 255, 255, 0.74);
  border-radius: 999px;
  padding: 0.18rem 0.52rem;
}

.composer-box {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 0.55rem;
  align-items: end;
  border: 1px solid #cbd9e4;
  border-radius: 24px;
  background: #fff;
  padding: 0.52rem 0.55rem 0.52rem 0.85rem;
  box-shadow: 0 10px 24px rgba(28, 45, 60, 0.1);
}

.composer-box textarea {
  min-height: 42px;
  max-height: 180px;
  border: 0;
  outline: none;
  resize: vertical;
  padding: 0.42rem 0;
  font: inherit;
  line-height: 1.5;
  background: transparent;
}

.composer-box button {
  align-self: stretch;
  border-radius: 18px;
  min-width: 76px;
}

button:disabled {
  opacity: 0.58;
  cursor: not-allowed;
}

@media (max-width: 1080px) {
  .ai-workbench {
    grid-template-columns: 72px minmax(0, 1fr);
  }

  .context-drawer {
    position: fixed;
    left: 5vw;
    top: 110px;
    bottom: 1rem;
    z-index: 40;
    width: min(380px, 88vw);
  }

  .chat-shell {
    grid-column: 2;
  }
}

@media (max-width: 720px) {
  .ai-workbench {
    grid-template-columns: 1fr;
  }

  .tool-rail {
    position: sticky;
    top: 0.4rem;
    z-index: 45;
    flex-direction: row;
    overflow-x: auto;
    border-radius: 18px;
  }

  .rail-nav {
    display: flex;
  }

  .tool-rail button {
    min-width: 70px;
  }

  .chat-shell {
    grid-column: 1;
    min-height: 70vh;
  }

  .chat-topbar {
    flex-direction: column;
  }

  .suggestion-grid {
    grid-template-columns: 1fr;
  }

  .message-bubble,
  .message-row.user .message-bubble {
    width: 100%;
    max-width: 100%;
  }

  .composer-box {
    grid-template-columns: 1fr;
    border-radius: 18px;
  }

  .composer-box button {
    min-height: 42px;
  }
}
</style>
