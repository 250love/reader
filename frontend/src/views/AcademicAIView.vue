<template>
  <section class="ai-workbench" :class="{ 'drawer-collapsed': drawerCollapsed }" @click="closeRunMenu">
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

      <section v-if="activeDrawer === 'context'" class="drawer-section context-section">
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

      <section v-else-if="activeDrawer === 'tasks'" class="drawer-section tasks-section">
        <div class="section-title-row drawer-hero-card">
          <div>
            <h4>快捷任务</h4>
            <p>选择论文后可直接运行。</p>
          </div>
          <span class="hero-badge">{{ normalTasks.length }} 个模板</span>
        </div>

        <div class="task-list">
          <button
            v-for="task in normalTasks"
            :key="task.key"
            :class="{ active: selectedTask === task.key }"
            :disabled="loading"
            @click="runTask(task.key)"
          >
            <span class="task-icon">{{ taskIconMap[task.key] || "AI" }}</span>
            <span class="task-copy">
              <strong>{{ task.label }}</strong>
              <span>{{ task.description }}</span>
            </span>
            <small>{{ taskModeLabel(task.mode) }}</small>
          </button>
        </div>
      </section>

      <section v-else-if="activeDrawer === 'model'" class="drawer-section model-section">
        <div class="section-title-row drawer-hero-card">
          <div>
            <h4>模型设置</h4>
            <p>复用账号设置中的 LLM Provider。</p>
          </div>
          <span class="hero-badge">{{ providers.length || 0 }} 个</span>
        </div>

        <div class="model-status-card">
          <span class="model-dot" :class="{ ready: providers.length > 0 }"></span>
          <div>
            <strong>{{ providers.length > 0 ? "Provider 已就绪" : "尚未配置 Provider" }}</strong>
            <p>{{ providers.length > 0 ? providerSummary : "请先在账号设置中添加 OpenAI-compatible 模型。" }}</p>
          </div>
        </div>

        <label class="field-label">
          <span>Provider</span>
          <select v-model="selectedProviderId" :disabled="providers.length === 0">
            <option value="">默认 Provider</option>
            <option v-for="provider in providers" :key="provider.id" :value="provider.id">
              {{ provider.name }} / {{ provider.model }}{{ provider.is_default ? "（默认）" : "" }}
            </option>
          </select>
        </label>

        <label class="field-label">
          <span>输出语言</span>
          <select v-model="targetLang">
            <option value="zh-CN">中文</option>
            <option value="en">English</option>
          </select>
        </label>

        <p v-if="providers.length === 0" class="warning-text">
          请先到账号设置中配置 LLM Provider，否则无法生成回答。
        </p>
      </section>

      <section v-else class="drawer-section history-section">
        <div class="section-title-row drawer-hero-card">
          <div>
            <h4>历史结果</h4>
            <p>像 ChatGPT 一样切换和管理持续对话。</p>
          </div>
          <span class="hero-badge">{{ visibleAgentRuns.length }} 条</span>
        </div>

        <button class="archive-open-btn" @click="openArchivedDialog">
          查看已归档对话
        </button>

        <div v-if="loadingRuns" class="placeholder-card">
          <strong>正在加载历史记录...</strong>
          <p>稍等片刻，最近生成会出现在这里。</p>
        </div>
        <p v-else-if="runsError" class="error-text">{{ runsError }}</p>
        <div v-else-if="visibleAgentRuns.length === 0" class="placeholder-card">
          <strong>暂无历史记录</strong>
          <p>生成一次回答后，系统会把结果保存到这里，方便回看和继续追问。</p>
        </div>

        <div v-else class="history-preview-list compact-scroll">
          <article
            v-for="run in visibleAgentRuns"
            :key="run.id"
            :class="['history-preview-card', 'run-card', { active: run.id === currentRunId, pending: run.pending }]"
            @click="restoreRun(run)"
            @contextmenu.prevent.stop="openRunMenu($event, run, 'active')"
          >
            <div>
              <strong>{{ runTitle(run) }}</strong>
              <p>{{ runSubtitle(run) }}</p>
              <small>{{ formatDateTime(run.created_at) }}</small>
            </div>
            <span v-if="run.pending" class="run-status">生成中</span>
          </article>
        </div>

        <section
          v-if="runMenu.open"
          class="run-context-menu"
          :style="{ left: `${runMenu.x}px`, top: `${runMenu.y}px` }"
          @click.stop
        >
          <button v-if="runMenu.scope === 'active'" @click="renameRunFromMenu">重命名</button>
          <button v-if="runMenu.scope === 'active'" @click="archiveRunFromMenu">归档</button>
          <button v-if="runMenu.scope === 'archived'" @click="restoreArchivedRunFromMenu">还原</button>
          <button class="danger" @click="deleteRunFromMenu">删除</button>
        </section>
      </section>
    </aside>

    <main class="chat-shell">
      <header class="chat-topbar">
        <div>
          <p class="brand-kicker">Academic AI</p>
          <h2 title="右键重命名对话" @contextmenu.prevent.stop="renameCurrentConversation">
            {{ conversationTitle }}
          </h2>
        </div>
        <div class="topbar-actions">
          <button v-if="drawerCollapsed" class="btn-secondary" @click="drawerCollapsed = false">展开工具栏</button>
          <button class="btn-secondary" :disabled="loadingData" @click="loadInitialData">
            {{ loadingData ? "刷新中..." : "刷新数据" }}
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
            <div v-else class="markdown-body" v-html="renderMarkdown(message.content)" />

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
          <span>{{ selectedPaperSummary }}</span>
          <span>{{ contextSummary }}</span>
          <span>{{ providerSummary }}</span>
        </div>
        <div class="composer-box">
          <textarea
            v-model="customQuery"
            rows="1"
            placeholder="输入你想问的问题，例如：这篇论文适合怎么汇报？"
            @keydown.enter.exact.prevent="submitCustomQuestion"
          />
          <button :disabled="loading" @click="submitCustomQuestion">发送</button>
        </div>
      </footer>
    </main>

    <section v-if="archivedDialogOpen" class="archive-dialog-backdrop" @click.self="closeArchivedDialog">
      <div class="archive-dialog">
        <header>
          <div>
            <p class="brand-kicker">Archived Chats</p>
            <h3>已归档对话</h3>
          </div>
          <button class="drawer-close" @click="closeArchivedDialog">×</button>
        </header>

        <p v-if="loadingArchivedRuns" class="muted-text">正在加载已归档对话...</p>
        <p v-else-if="archivedRunsError" class="error-text">{{ archivedRunsError }}</p>
        <div v-else-if="archivedRuns.length === 0" class="placeholder-card">
          <strong>暂无归档对话</strong>
          <p>在历史卡片上右键选择“归档”后，会出现在这里。</p>
        </div>

        <div v-else class="archive-card-list compact-scroll">
          <article
            v-for="run in archivedRuns"
            :key="run.id"
            class="history-preview-card run-card"
            @contextmenu.prevent.stop="openRunMenu($event, run, 'archived')"
          >
            <div>
              <strong>{{ runTitle(run) }}</strong>
              <p>{{ runSubtitle(run) }}</p>
              <small>{{ formatDateTime(run.updated_at || run.created_at) }}</small>
            </div>
          </article>
        </div>
      </div>
    </section>
  </section>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref } from "vue";
import { useRoute } from "vue-router";

import {
  deleteAgentRun,
  fetchAgentTasks,
  fetchAgentRun,
  fetchAgentRuns,
  fetchPapers,
  fetchProviders,
  runAcademicAgent,
  updateAgentRun
} from "@/services/api";

const route = useRoute();

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
const agentRuns = ref([]);
const currentRunId = ref("");
const currentRunDraft = ref(null);
const currentConversationTitle = ref("");
const activeDrawer = ref("context");
const drawerCollapsed = ref(false);
const messageListRef = ref(null);
const loadingRuns = ref(false);
const runsError = ref("");
const archivedDialogOpen = ref(false);
const archivedRuns = ref([]);
const loadingArchivedRuns = ref(false);
const archivedRunsError = ref("");
const runMenu = reactive({
  open: false,
  x: 0,
  y: 0,
  runId: "",
  scope: "active"
});

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

const taskIconMap = {
  paper_summary: "速",
  method_breakdown: "拆",
  innovation_limits: "新",
  presentation_outline: "纲",
  paper_compare: "比"
};

function taskModeLabel(mode) {
  if (mode === "single") return "需 1 篇";
  if (mode === "multi") return "需 2-3 篇";
  return "0-3 篇";
}

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

const taskLabelMap = computed(() => {
  const labels = {};
  for (const task of tasks.value) {
    labels[task.key] = task.label;
  }
  return labels;
});

const conversationTitle = computed(() => currentConversationTitle.value || "新对话");

const visibleAgentRuns = computed(() => {
  const rows = [...agentRuns.value];
  const draft = currentRunDraft.value;
  if (!draft) return rows;

  const existingIndex = rows.findIndex((run) => run.id === draft.id);
  if (existingIndex >= 0) {
    rows[existingIndex] = { ...rows[existingIndex], ...draft };
    return rows;
  }
  return [draft, ...rows];
});

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

const selectedPaperSummary = computed(() => (
  selectedPaperIds.value.length > 0 ? `${selectedPaperIds.value.length} 篇论文` : "未选择论文 · 通用对话"
));

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
    await loadAgentRuns();
  } catch (error) {
    dataError.value = error?.response?.data?.error || "学术 AI 数据加载失败，请稍后重试。";
  } finally {
    loadingData.value = false;
  }
}

async function loadAgentRuns() {
  loadingRuns.value = true;
  runsError.value = "";
  try {
    agentRuns.value = await fetchAgentRuns({ limit: 100 });
  } catch (error) {
    runsError.value = error?.response?.data?.error || "历史记录加载失败。";
  } finally {
    loadingRuns.value = false;
  }
}

async function loadArchivedRuns() {
  loadingArchivedRuns.value = true;
  archivedRunsError.value = "";
  try {
    archivedRuns.value = await fetchAgentRuns({ limit: 100, archived: true });
  } catch (error) {
    archivedRunsError.value = error?.response?.data?.error || "已归档对话加载失败。";
  } finally {
    loadingArchivedRuns.value = false;
  }
}

async function openArchivedDialog() {
  closeRunMenu();
  archivedDialogOpen.value = true;
  await loadArchivedRuns();
}

function closeArchivedDialog() {
  archivedDialogOpen.value = false;
  closeRunMenu();
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
  if (task.mode === "single_or_multi" && count > 3) return "自定义提问最多选择 3 篇论文。";
  if (taskKey === "custom_qa" && !queryText.trim()) return "请输入自定义问题。";
  return "";
}

function buildUserPrompt(taskKey, queryText) {
  const task = tasks.value.find((item) => item.key === taskKey);
  if (taskKey === "custom_qa") return queryText.trim();
  return `请基于已选论文执行「${task?.label || taskKey}」。`;
}

function buildConversationTitle(taskKey, userPrompt, sources = []) {
  const taskLabel = taskLabelMap.value[taskKey] || taskKey || "学术 AI";
  const sourceTitles = (sources || [])
    .map((source) => truncateText(source.title, 18))
    .filter(Boolean);

  if (taskKey === "custom_qa" && userPrompt) return truncateText(userPrompt, 32);
  if (taskKey === "paper_compare" && sourceTitles.length >= 2) {
    return `多篇对比：${sourceTitles[0]} / ${sourceTitles[1]}`;
  }
  if (sourceTitles.length) return `${sourceTitles[0]} · ${taskLabel}`;
  if (userPrompt) return `${taskLabel}讨论`;
  return taskLabel;
}

function escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function sanitizeUrl(url) {
  const clean = String(url || "").trim();
  if (/^(https?:|mailto:)/i.test(clean)) return escapeHtml(clean);
  if (clean.startsWith("#") || clean.startsWith("/")) return escapeHtml(clean);
  return "";
}

function renderInlineMarkdown(text) {
  let out = escapeHtml(text);
  out = out.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (_match, alt, url) => {
    const safeUrl = sanitizeUrl(url);
    return safeUrl ? `<a href="${safeUrl}" target="_blank" rel="noreferrer">${alt || safeUrl}</a>` : alt;
  });
  out = out.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_match, label, url) => {
    const safeUrl = sanitizeUrl(url);
    return safeUrl ? `<a href="${safeUrl}" target="_blank" rel="noreferrer">${label}</a>` : label;
  });
  return out
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/__(.+?)__/g, "<strong>$1</strong>")
    .replace(/~~(.+?)~~/g, "<del>$1</del>")
    .replace(/(^|[^*])\*([^*\n]+)\*/g, "$1<em>$2</em>")
    .replace(/(^|[^_])_([^_\n]+)_/g, "$1<em>$2</em>");
}

function isTableSeparator(line) {
  return /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(line);
}

function parseTable(lines, startIndex) {
  if (startIndex + 1 >= lines.length || !lines[startIndex].includes("|") || !isTableSeparator(lines[startIndex + 1])) {
    return null;
  }

  const rows = [];
  let index = startIndex;
  while (index < lines.length && lines[index].includes("|") && lines[index].trim()) {
    if (!isTableSeparator(lines[index])) {
      rows.push(lines[index]);
    }
    index += 1;
  }

  if (rows.length < 2) return null;

  const cellsFor = (row) => row
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => renderInlineMarkdown(cell.trim()));

  const [head, ...body] = rows.map(cellsFor);
  const thead = `<thead><tr>${head.map((cell) => `<th>${cell}</th>`).join("")}</tr></thead>`;
  const tbody = `<tbody>${body
    .map((row) => `<tr>${row.map((cell) => `<td>${cell}</td>`).join("")}</tr>`)
    .join("")}</tbody>`;
  return {
    html: `<div class="markdown-table-wrap"><table>${thead}${tbody}</table></div>`,
    nextIndex: index
  };
}

function renderMarkdown(markdown) {
  const lines = String(markdown || "").replace(/\r\n/g, "\n").split("\n");
  const html = [];
  let index = 0;
  let inCode = false;
  let codeLines = [];
  let listItems = [];
  let listType = "";
  let paragraph = [];

  function flushParagraph() {
    if (!paragraph.length) return;
    html.push(`<p>${renderInlineMarkdown(paragraph.join(" "))}</p>`);
    paragraph = [];
  }

  function flushList() {
    if (!listItems.length) return;
    const tag = listType || "ul";
    html.push(`<${tag}>${listItems.map((item) => `<li>${renderInlineMarkdown(item)}</li>`).join("")}</${tag}>`);
    listItems = [];
    listType = "";
  }

  function flushCode() {
    html.push(`<pre class="code-block"><code>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
    codeLines = [];
  }

  while (index < lines.length) {
    const line = lines[index];
    const trimmed = line.trim();

    if (trimmed.startsWith("```")) {
      flushParagraph();
      flushList();
      if (inCode) {
        flushCode();
        inCode = false;
      } else {
        inCode = true;
        codeLines = [];
      }
      index += 1;
      continue;
    }

    if (inCode) {
      codeLines.push(line);
      index += 1;
      continue;
    }

    const table = parseTable(lines, index);
    if (table) {
      flushParagraph();
      flushList();
      html.push(table.html);
      index = table.nextIndex;
      continue;
    }

    if (!trimmed) {
      flushParagraph();
      flushList();
      index += 1;
      continue;
    }

    if (/^[-*_]{3,}$/.test(trimmed)) {
      flushParagraph();
      flushList();
      html.push("<hr />");
      index += 1;
      continue;
    }

    const quote = trimmed.match(/^>\s?(.+)$/);
    if (quote) {
      flushParagraph();
      flushList();
      const quoteLines = [];
      while (index < lines.length) {
        const quoteMatch = lines[index].trim().match(/^>\s?(.+)$/);
        if (!quoteMatch) break;
        quoteLines.push(quoteMatch[1]);
        index += 1;
      }
      html.push(`<blockquote>${renderInlineMarkdown(quoteLines.join(" "))}</blockquote>`);
      continue;
    }

    const heading = trimmed.match(/^(#{1,3})\s+(.+)$/);
    if (heading) {
      flushParagraph();
      flushList();
      const level = Math.min(6, heading[1].length + 2);
      html.push(`<h${level}>${renderInlineMarkdown(heading[2])}</h${level}>`);
      index += 1;
      continue;
    }

    const unordered = trimmed.match(/^[-*]\s+(.+)$/);
    const ordered = trimmed.match(/^\d+\.\s+(.+)$/);
    const list = unordered || ordered;
    if (list) {
      flushParagraph();
      const currentType = ordered ? "ol" : "ul";
      if (listType && listType !== currentType) {
        flushList();
      }
      listType = currentType;
      listItems.push(list[1]);
      index += 1;
      continue;
    }

    paragraph.push(trimmed);
    index += 1;
  }

  flushParagraph();
  flushList();
  if (inCode) flushCode();
  return html.join("");
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
    runId: "",
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
  const userPrompt = options.regenerate
    ? `重新生成：${buildUserPrompt(taskKey, queryText)}`
    : buildUserPrompt(taskKey, queryText);
  const conversationId = currentRunId.value || "";
  const draftTitle = conversationId ? conversationTitle.value : "新对话";
  const payload = {
    task: taskKey,
    paper_ids: [...selectedPaperIds.value],
    query: queryText,
    user_prompt: userPrompt,
    conversation_id: conversationId || undefined,
    provider_id: selectedProviderId.value || undefined,
    target_lang: targetLang.value,
    context_options: { ...contextOptions }
  };

  const userMessage = makeMessage("user", {
    label: task?.label || "自定义提问",
    content: userPrompt
  });
  const assistantMessage = makeMessage("assistant", {
    label: task?.label || "学术 AI",
    content: "正在生成回答...",
    loading: true,
    payload
  });

  if (taskKey === "custom_qa" && !options.regenerate) {
    customQuery.value = "";
  }
  messages.value.push(userMessage, assistantMessage);
  if (!conversationId) {
    currentRunId.value = "";
  }
  currentConversationTitle.value = draftTitle;
  currentRunDraft.value = {
    id: conversationId || "__current_pending",
    task: taskKey,
    title: draftTitle,
    user_prompt: userPrompt,
    query: queryText,
    paper_ids: [...selectedPaperIds.value],
    sources: [],
    created_at: new Date().toISOString(),
    pending: true
  };
  loading.value = true;
  await scrollToBottom();

  try {
    const result = await runAcademicAgent(payload);
    Object.assign(assistantMessage, {
      content: result.answer || "",
      loading: false,
      sources: result.sources || [],
      suggestedQuestions: result.suggested_questions || [],
      runId: result.run_id || "",
      payload: { ...payload, conversation_id: result.run_id || conversationId || undefined }
    });
    const nextTitle = result.title || buildConversationTitle(taskKey, userPrompt, result.sources || []);
    currentRunId.value = result.run_id || "";
    currentConversationTitle.value = nextTitle;
    currentRunDraft.value = result.run_id
      ? {
          id: result.run_id,
          task: taskKey,
          title: nextTitle,
          user_prompt: result.user_prompt || userPrompt,
          query: queryText,
          paper_ids: [...selectedPaperIds.value],
          sources: result.sources || [],
          created_at: currentRunDraft.value?.created_at || new Date().toISOString(),
          updated_at: new Date().toISOString(),
          pending: false
        }
      : null;
    await loadAgentRuns();
    currentRunDraft.value = null;
  } catch (error) {
    currentRunDraft.value = null;
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

function submitCustomQuestion() {
  runTask("custom_qa");
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

function truncateText(value, maxLength = 34) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  if (text.length <= maxLength) return text;
  return `${text.slice(0, maxLength)}...`;
}

function runTitle(run) {
  if (run.title) return run.title;
  const label = taskLabelMap.value[run.task] || run.task || "学术 AI";
  const firstSource = run.sources?.[0]?.title || "";
  if (firstSource) return `${truncateText(firstSource, 18)} · ${label}`;
  if (run.paper_ids?.length) return `${run.paper_ids.length} 篇论文 · ${label}`;
  return `通用对话 · ${label}`;
}

function runSubtitle(run) {
  if (run.pending) return "正在生成回答...";
  if (run.user_prompt) return truncateText(run.user_prompt, 46);
  if (run.query) return truncateText(run.query, 46);
  if (Array.isArray(run.messages) && run.messages.length > 0) {
    const lastUser = [...run.messages].reverse().find((message) => message.role === "user");
    if (lastUser?.content) return truncateText(lastUser.content, 46);
  }
  const count = Array.isArray(run.paper_ids) ? run.paper_ids.length : 0;
  if (count > 0) return `${count} 篇论文上下文 · 点击回显回答`;
  return "未选择论文上下文 · 点击回显回答";
}

function formatDateTime(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(date);
}

function patchRunInList(runId, patch) {
  agentRuns.value = agentRuns.value.map((run) => (
    run.id === runId ? { ...run, ...patch } : run
  ));
  if (currentRunDraft.value?.id === runId) {
    currentRunDraft.value = { ...currentRunDraft.value, ...patch };
  }
}

function openRunMenu(event, run, scope = "active") {
  if (!run || run.pending) return;
  runMenu.open = true;
  runMenu.x = event.clientX;
  runMenu.y = event.clientY;
  runMenu.runId = run.id || "";
  runMenu.scope = scope;
}

function closeRunMenu() {
  runMenu.open = false;
}

function selectedMenuRun() {
  const list = runMenu.scope === "archived" ? archivedRuns.value : visibleAgentRuns.value;
  return list.find((run) => run.id === runMenu.runId);
}

function payloadFromMessage(message, run) {
  return {
    task: message.task || run.task || "custom_qa",
    paper_ids: (message.paper_ids || run.paper_ids || []).map(String),
    query: message.query || run.query || "",
    user_prompt: message.content || run.user_prompt || "",
    conversation_id: run.id,
    provider_id: run.provider_id || undefined,
    target_lang: targetLang.value,
    context_options: { ...contextOptions }
  };
}

function messagesFromRun(run) {
  const stored = Array.isArray(run.messages) ? run.messages : [];
  const sourceMessages = stored.length
    ? stored
    : [
        {
          role: "user",
          label: taskLabelMap.value[run.task] || run.task || "学术 AI",
          content: run.user_prompt || run.query || runTitle(run),
          task: run.task,
          query: run.query,
          paper_ids: run.paper_ids || []
        },
        {
          role: "assistant",
          label: taskLabelMap.value[run.task] || run.task || "学术 AI",
          content: run.answer || "",
          task: run.task,
          query: run.query,
          paper_ids: run.paper_ids || [],
          sources: run.sources || [],
          suggested_questions: run.suggested_questions || []
        }
      ];

  return sourceMessages
    .filter((message) => message?.content)
    .map((message) => makeMessage(message.role || "assistant", {
      label: message.label || taskLabelMap.value[message.task] || "学术 AI",
      content: message.content || "",
      sources: message.sources || [],
      suggestedQuestions: message.suggested_questions || [],
      runId: run.id || "",
      payload: message.role === "assistant" ? payloadFromMessage(message, run) : null
    }));
}

async function renameRun(run, title) {
  const nextTitle = String(title || "").trim();
  if (!run?.id || !nextTitle) return;

  const updated = await updateAgentRun(run.id, { title: nextTitle });
  patchRunInList(run.id, { title: updated.title || nextTitle });
  if (currentRunId.value === run.id) {
    currentConversationTitle.value = updated.title || nextTitle;
  }
}

async function renameRunFromMenu() {
  const run = selectedMenuRun();
  closeRunMenu();
  if (!run) return;
  const nextTitle = window.prompt("重命名对话", runTitle(run));
  if (nextTitle === null) return;
  try {
    await renameRun(run, nextTitle);
  } catch (error) {
    noticeMessage.value = error?.response?.data?.error || "重命名失败。";
  }
}

async function archiveRunFromMenu() {
  const run = selectedMenuRun();
  closeRunMenu();
  if (!run?.id) return;
  try {
    await updateAgentRun(run.id, { archived: true });
    agentRuns.value = agentRuns.value.filter((item) => item.id !== run.id);
    if (currentRunId.value === run.id) {
      clearConversation();
    }
  } catch (error) {
    noticeMessage.value = error?.response?.data?.error || "归档失败。";
  }
}

async function restoreArchivedRunFromMenu() {
  const run = selectedMenuRun();
  closeRunMenu();
  if (!run?.id) return;
  try {
    await updateAgentRun(run.id, { archived: false });
    archivedRuns.value = archivedRuns.value.filter((item) => item.id !== run.id);
    await loadAgentRuns();
  } catch (error) {
    noticeMessage.value = error?.response?.data?.error || "还原失败。";
  }
}

async function deleteRunFromMenu() {
  const run = selectedMenuRun();
  const scope = runMenu.scope;
  closeRunMenu();
  if (!run?.id) return;
  const ok = window.confirm(`确认删除「${runTitle(run)}」吗？`);
  if (!ok) return;
  if (scope === "archived") {
    try {
      await deleteAgentRun(run.id);
      archivedRuns.value = archivedRuns.value.filter((item) => item.id !== run.id);
    } catch (error) {
      noticeMessage.value = error?.response?.data?.error || "删除历史记录失败。";
    }
    return;
  }
  await removeRun(run.id);
}

async function renameCurrentConversation() {
  const run = currentRunId.value
    ? visibleAgentRuns.value.find((item) => item.id === currentRunId.value)
    : null;
  const nextTitle = window.prompt("重命名对话", conversationTitle.value);
  if (nextTitle === null) return;
  const cleanTitle = nextTitle.trim();
  if (!cleanTitle) return;

  if (!run?.id) {
    currentConversationTitle.value = cleanTitle;
    if (currentRunDraft.value) currentRunDraft.value = { ...currentRunDraft.value, title: cleanTitle };
    return;
  }

  try {
    await renameRun(run, cleanTitle);
  } catch (error) {
    noticeMessage.value = error?.response?.data?.error || "重命名失败。";
  }
}

async function restoreRun(run) {
  if (!run || run.pending) return;
  closeRunMenu();
  let detail = run;
  try {
    detail = await fetchAgentRun(run.id);
  } catch (error) {
    noticeMessage.value = error?.response?.data?.error || "对话加载失败。";
    return;
  }

  selectedTask.value = detail.task || selectedTask.value;
  selectedPaperIds.value = Array.isArray(detail.paper_ids) ? detail.paper_ids.map(String) : [];
  selectedProviderId.value = detail.provider_id || selectedProviderId.value;
  currentRunId.value = detail.id || "";
  currentRunDraft.value = null;
  currentConversationTitle.value = runTitle(detail);
  messages.value = messagesFromRun(detail);
  noticeMessage.value = "";
  await scrollToBottom();
}

async function removeRun(runId) {
  if (!runId) return;
  try {
    await deleteAgentRun(runId);
    agentRuns.value = agentRuns.value.filter((run) => run.id !== runId);
    if (currentRunId.value === runId) {
      clearConversation();
    }
    noticeMessage.value = "历史记录已删除。";
  } catch (error) {
    noticeMessage.value = error?.response?.data?.error || "删除历史记录失败。";
  }
}

function clearConversation() {
  messages.value = [];
  noticeMessage.value = "";
  currentRunId.value = "";
  currentRunDraft.value = null;
  currentConversationTitle.value = "";
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
  height: calc(100vh - 150px);
  min-height: 640px;
  display: grid;
  grid-template-columns: 82px minmax(280px, 360px) minmax(0, 1fr);
  gap: 0.75rem;
  overflow: hidden;
}

.ai-workbench.drawer-collapsed {
  grid-template-columns: 82px minmax(0, 1fr);
}

.ai-workbench.drawer-collapsed .chat-shell {
  grid-column: 2;
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

.context-drawer {
  border-radius: 22px;
  padding: 0.9rem;
  min-height: 0;
  overflow: hidden;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
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
  min-height: 0;
}

.context-section {
  grid-template-rows: auto auto minmax(0, 1fr) auto;
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

.drawer-hero-card {
  align-items: center;
  border: 1px solid rgba(190, 215, 223, 0.82);
  border-radius: 18px;
  padding: 0.78rem;
  background:
    radial-gradient(circle at 12% 0%, rgba(160, 218, 205, 0.36), transparent 38%),
    linear-gradient(135deg, rgba(255, 255, 255, 0.94), rgba(241, 249, 246, 0.9));
  box-shadow: 0 12px 28px rgba(35, 57, 75, 0.08);
}

.drawer-hero-card h4 {
  font-family: "Space Grotesk", "IBM Plex Sans", sans-serif;
  font-size: 1.05rem;
}

.hero-badge {
  flex: 0 0 auto;
  border: 1px solid rgba(15, 109, 100, 0.2);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.76);
  color: #0f6d64;
  font-size: 0.78rem;
  font-weight: 800;
  padding: 0.22rem 0.54rem;
}

.archive-open-btn {
  justify-self: stretch;
  border: 1px solid #cbd9e4;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.84);
  color: #23394b;
  font-weight: 800;
  padding: 0.72rem 0.82rem;
  text-align: left;
}

.archive-open-btn:hover {
  background: #eef8f4;
  border-color: #b8dfd2;
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
  min-height: 0;
  max-height: none;
  overflow-y: auto;
  padding-right: 0.18rem;
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
  flex: 0 0 auto;
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
  grid-template-columns: 42px minmax(0, 1fr) auto;
  align-items: center;
  gap: 0.68rem;
  border-radius: 18px;
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.98), rgba(248, 252, 250, 0.96));
  color: #23394b;
  border: 1px solid #d5e0e8;
  padding: 0.76rem;
  box-shadow: 0 10px 22px rgba(31, 52, 69, 0.055);
  transition: transform 0.16s ease, border-color 0.16s ease, background 0.16s ease, box-shadow 0.16s ease;
}

.task-list button:hover,
.task-list button.active {
  background: #e9f6f2;
  border-color: #b7ded1;
  box-shadow: 0 14px 30px rgba(20, 92, 80, 0.12);
  transform: translateY(-1px);
}

.task-icon {
  width: 42px;
  height: 42px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  background: #eff8f5;
  color: #0f6d64;
  font-weight: 900;
  font-size: 1.08rem;
}

.task-list button.active .task-icon {
  background: #0f6d64;
  color: #fff;
}

.task-copy {
  min-width: 0;
  display: grid;
  gap: 0.18rem;
}

.task-copy strong {
  color: #1f3445;
  font-size: 0.98rem;
}

.task-copy span {
  color: #607789;
  font-size: 0.86rem;
}

.task-list button > small {
  align-self: start;
  border: 1px solid #d5e7e2;
  border-radius: 999px;
  color: #587184;
  background: rgba(255, 255, 255, 0.72);
  font-size: 0.72rem;
  font-weight: 800;
  padding: 0.18rem 0.42rem;
  white-space: nowrap;
}

.field-label {
  display: grid;
  gap: 0.58rem;
  border: 1px solid #d5e0e8;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.82);
  padding: 0.78rem;
  color: #33495a;
  font-size: 0.92rem;
  font-weight: 700;
  box-shadow: 0 10px 24px rgba(31, 52, 69, 0.06);
}

.field-label > span {
  color: #22394c;
}

.field-label select {
  min-height: 48px;
  border-radius: 14px;
  font-weight: 800;
}

.model-section,
.history-section,
.tasks-section {
  align-content: start;
}

.model-status-card {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 0.72rem;
  align-items: start;
  border: 1px solid rgba(181, 211, 203, 0.86);
  border-radius: 18px;
  background: linear-gradient(135deg, rgba(237, 250, 246, 0.92), rgba(255, 255, 255, 0.86));
  padding: 0.82rem;
}

.model-status-card strong,
.history-preview-card strong {
  color: #1f3445;
}

.model-status-card p,
.history-preview-card p {
  margin: 0.22rem 0 0;
  color: #607789;
  font-size: 0.88rem;
  line-height: 1.55;
}

.model-dot {
  width: 12px;
  height: 12px;
  margin-top: 0.34rem;
  border-radius: 999px;
  background: #c6d2dc;
  box-shadow: 0 0 0 5px rgba(198, 210, 220, 0.18);
}

.model-dot.ready {
  background: #16a085;
  box-shadow: 0 0 0 5px rgba(22, 160, 133, 0.14);
}

.history-preview-list {
  display: grid;
  gap: 0.62rem;
}

.history-preview-card {
  border: 1px solid #d5e0e8;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.86);
  padding: 0.78rem;
  box-shadow: 0 10px 24px rgba(31, 52, 69, 0.055);
}

.run-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 0.6rem;
  align-items: start;
  cursor: pointer;
  transition: transform 0.16s ease, border-color 0.16s ease, box-shadow 0.16s ease;
}

.run-card:hover {
  border-color: #b7ded1;
  box-shadow: 0 14px 30px rgba(20, 92, 80, 0.12);
  transform: translateY(-1px);
}

.run-card.active,
.run-card.pending {
  border-color: rgba(15, 109, 100, 0.38);
  background: linear-gradient(135deg, rgba(229, 247, 240, 0.96), rgba(255, 255, 255, 0.88));
}

.run-card small {
  display: block;
  margin-top: 0.42rem;
  color: #7a8da0;
}

.run-status {
  border: 1px solid rgba(15, 109, 100, 0.18);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
  color: #0f6d64;
  font-size: 0.72rem;
  font-weight: 800;
  padding: 0.2rem 0.46rem;
  white-space: nowrap;
}

.run-context-menu {
  position: fixed;
  z-index: 80;
  width: 132px;
  border: 1px solid #cfdde6;
  border-radius: 14px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 18px 38px rgba(20, 36, 50, 0.18);
  padding: 0.28rem;
}

.run-context-menu button {
  width: 100%;
  border: 0;
  border-radius: 10px;
  background: transparent;
  color: #24394a;
  text-align: left;
  padding: 0.52rem 0.62rem;
}

.run-context-menu button:hover {
  background: #eef7f4;
}

.run-context-menu button.danger {
  color: #b63838;
}

.archive-dialog-backdrop {
  position: fixed;
  inset: 0;
  z-index: 70;
  display: grid;
  place-items: center;
  background: rgba(20, 36, 50, 0.22);
  backdrop-filter: blur(2px);
}

.archive-dialog {
  width: min(560px, 92vw);
  max-height: min(720px, 86vh);
  border: 1px solid rgba(190, 207, 218, 0.9);
  border-radius: 24px;
  background:
    radial-gradient(circle at 12% 0%, rgba(209, 236, 230, 0.66), transparent 34%),
    color-mix(in srgb, var(--card), white 30%);
  box-shadow: 0 24px 60px rgba(20, 36, 50, 0.26);
  padding: 1rem;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 0.85rem;
}

.archive-dialog header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  border-bottom: 1px solid rgba(200, 214, 224, 0.75);
  padding-bottom: 0.8rem;
}

.archive-dialog h3 {
  margin: 0.15rem 0 0;
  font-family: "Space Grotesk", "IBM Plex Sans", sans-serif;
}

.archive-card-list {
  display: grid;
  gap: 0.62rem;
  overflow-y: auto;
  padding-right: 0.18rem;
}

.history-preview-card.muted {
  border-style: dashed;
  background: rgba(251, 253, 255, 0.76);
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
  min-height: 0;
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

.chat-topbar > div:first-child {
  min-width: 0;
}

.chat-topbar h2 {
  max-width: min(820px, 58vw);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: context-menu;
}

.topbar-actions {
  flex-wrap: wrap;
  justify-content: flex-end;
}

.message-list {
  min-height: 0;
  height: 100%;
  overflow-y: auto;
  padding: 1.1rem clamp(1rem, 3vw, 3rem);
  scroll-behavior: smooth;
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

.message-bubble p {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.68;
  font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
}

.markdown-body {
  color: #213544;
  line-height: 1.7;
  word-break: break-word;
}

.message-row.user .markdown-body {
  color: #fff;
}

.markdown-body :deep(p) {
  margin: 0.35rem 0;
}

.markdown-body :deep(h3),
.markdown-body :deep(h4),
.markdown-body :deep(h5) {
  margin: 0.85rem 0 0.4rem;
  font-family: "Space Grotesk", "IBM Plex Sans", sans-serif;
  line-height: 1.35;
}

.markdown-body :deep(ul) {
  margin: 0.35rem 0 0.6rem;
  padding-left: 1.25rem;
}

.markdown-body :deep(ol) {
  margin: 0.35rem 0 0.6rem;
  padding-left: 1.45rem;
}

.markdown-body :deep(li) {
  margin: 0.18rem 0;
}

.markdown-body :deep(a) {
  color: #0b6a61;
  font-weight: 700;
}

.markdown-body :deep(code) {
  border: 1px solid #d6e0e8;
  border-radius: 6px;
  background: #f5f8fb;
  padding: 0.08rem 0.28rem;
  font-family: "Cascadia Code", "Consolas", monospace;
  font-size: 0.92em;
}

.message-row.user .markdown-body :deep(a) {
  color: #eafffb;
}

.message-row.user .markdown-body :deep(code) {
  border-color: rgba(255, 255, 255, 0.35);
  background: rgba(255, 255, 255, 0.14);
  color: #fff;
}

.markdown-body :deep(.code-block) {
  margin: 0.6rem 0;
  white-space: pre;
  overflow-x: auto;
  border: 1px solid #d6e0e8;
  border-radius: 12px;
  background: #f5f8fb;
  padding: 0.72rem;
}

.message-row.user .markdown-body :deep(.code-block) {
  border-color: rgba(255, 255, 255, 0.32);
  background: rgba(255, 255, 255, 0.12);
}

.markdown-body :deep(.code-block code) {
  border: 0;
  background: transparent;
  padding: 0;
}

.markdown-body :deep(blockquote) {
  margin: 0.6rem 0;
  border-left: 4px solid #b8dcd2;
  background: #f5faf8;
  border-radius: 0 10px 10px 0;
  padding: 0.52rem 0.72rem;
  color: #3f5a6d;
}

.message-row.user .markdown-body :deep(blockquote) {
  border-left-color: rgba(255, 255, 255, 0.55);
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
}

.markdown-body :deep(hr) {
  border: 0;
  border-top: 1px solid #dce6ec;
  margin: 0.85rem 0;
}

.message-row.user .markdown-body :deep(hr) {
  border-top-color: rgba(255, 255, 255, 0.35);
}

.markdown-body :deep(.markdown-table-wrap) {
  margin: 0.65rem 0;
  overflow-x: auto;
}

.markdown-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
  border: 1px solid #d6e0e8;
  border-radius: 12px;
  overflow: hidden;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  border-bottom: 1px solid #e1e8ee;
  padding: 0.54rem 0.62rem;
  text-align: left;
  vertical-align: top;
}

.markdown-body :deep(th) {
  background: #eef5f8;
  color: #263d4f;
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
  position: relative;
  bottom: 0;
  padding: 0.85rem clamp(1rem, 3vw, 3rem) 1rem;
  background: linear-gradient(180deg, rgba(255, 250, 242, 0.72), rgba(255, 250, 242, 0.98) 32%);
  border-top: 1px solid rgba(210, 222, 230, 0.78);
  z-index: 5;
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

  .ai-workbench.drawer-collapsed {
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
  .ai-workbench,
  .ai-workbench.drawer-collapsed {
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

  .chat-shell,
  .ai-workbench.drawer-collapsed .chat-shell {
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
