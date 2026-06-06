<template>
  <section class="academic-ai-layout">
    <header class="academic-ai-hero">
      <div>
        <p class="brand-kicker">Academic AI</p>
        <h2>学术 AI 助手</h2>
        <p>基于你的文献库，快速完成论文速读、方法拆解、多篇对比和汇报准备。</p>
      </div>
      <button class="btn-secondary" @click="loadInitialData" :disabled="loadingData">
        {{ loadingData ? "刷新中..." : "刷新数据" }}
      </button>
    </header>

    <section class="academic-ai-workspace">
      <aside class="card paper-picker-panel">
        <div class="panel-head">
          <div>
            <h3>选择论文</h3>
            <p>{{ selectedPaperIds.length }} / {{ papers.length }} 篇已选择</p>
          </div>
          <button class="btn-secondary" @click="clearSelection" :disabled="selectedPaperIds.length === 0">
            清空选择
          </button>
        </div>

        <input v-model="paperSearch" class="paper-search" placeholder="搜索标题、作者、来源或年份" />

        <p v-if="loadingData" class="muted-text">正在加载文献...</p>
        <p v-else-if="dataError" class="error-text">{{ dataError }}</p>
        <p v-else-if="papers.length === 0" class="muted-text">暂无文献，请先在论文管理中导入 PDF。</p>
        <p v-else-if="filteredPapers.length === 0" class="muted-text">没有匹配的论文。</p>

        <div v-else class="paper-list">
          <label
            v-for="paper in filteredPapers"
            :key="paper.id"
            :class="['paper-option', { selected: selectedIdSet.has(paper.id) }]"
          >
            <input type="checkbox" :checked="selectedIdSet.has(paper.id)" @change="togglePaper(paper.id)" />
            <div>
              <h4>{{ paper.title || "Untitled" }}</h4>
              <p>{{ paper.authors || "未知作者" }}</p>
              <span>{{ paper.conference || "未填写来源" }} · {{ paper.year || "n.d." }}</span>
              <div v-if="Array.isArray(paper.tags) && paper.tags.length" class="tag-row">
                <small v-for="tag in paper.tags.slice(0, 4)" :key="tag">{{ tag }}</small>
              </div>
            </div>
          </label>
        </div>
      </aside>

      <section class="task-result-panel">
        <article class="card config-card">
          <div class="panel-head">
            <div>
              <h3>任务与上下文</h3>
              <p>{{ currentTaskHint }}</p>
            </div>
            <label class="target-lang">
              输出语言
              <select v-model="targetLang">
                <option value="zh-CN">中文</option>
                <option value="en">English</option>
              </select>
            </label>
          </div>

          <div class="provider-row">
            <label>
              模型配置
              <select v-model="selectedProviderId" :disabled="providers.length === 0">
                <option value="">默认 Provider</option>
                <option v-for="provider in providers" :key="provider.id" :value="provider.id">
                  {{ provider.name }} / {{ provider.model }}{{ provider.is_default ? "（默认）" : "" }}
                </option>
              </select>
            </label>
            <p v-if="providers.length === 0" class="warning-text">
              请先到账号设置中配置 LLM Provider。
            </p>
          </div>

          <div class="context-options">
            <label><input v-model="contextOptions.include_metadata" type="checkbox" /> 文献信息</label>
            <label><input v-model="contextOptions.include_pdf_excerpt" type="checkbox" /> PDF 摘要内容</label>
            <label><input v-model="contextOptions.include_annotations" type="checkbox" /> 我的高亮笔记</label>
            <label><input v-model="contextOptions.include_figures" type="checkbox" /> 图表说明</label>
          </div>

          <div class="task-buttons">
            <button
              v-for="task in normalTasks"
              :key="task.key"
              :class="{ active: selectedTask === task.key }"
              :disabled="loading || providers.length === 0"
              @click="runTask(task.key)"
            >
              {{ task.label }}
            </button>
          </div>

          <div class="custom-qa-box">
            <label>
              自定义问题
              <textarea v-model="customQuery" rows="3" placeholder="请输入你想问的问题，例如：这篇论文最适合从哪些角度汇报？" />
            </label>
            <button :disabled="loading || providers.length === 0" @click="runTask('custom_qa')">
              自定义提问
            </button>
          </div>
        </article>

        <article class="card result-card">
          <div class="panel-head">
            <div>
              <h3>AI 输出</h3>
              <p>{{ selectedTaskLabel }}</p>
            </div>
            <div class="result-actions">
              <button class="btn-secondary" @click="copyMarkdown" :disabled="!answer">复制 Markdown</button>
              <button class="btn-secondary" @click="clearResult" :disabled="!answer && !errorMessage">清空结果</button>
            </div>
          </div>

          <p v-if="loading" class="loading-text">学术 AI 正在分析论文，请稍候...</p>
          <p v-else-if="errorMessage" class="error-text">{{ errorMessage }}</p>
          <pre v-else-if="answer" class="answer-box">{{ answer }}</pre>
          <p v-else class="muted-text">选择论文和任务后，AI 生成结果会显示在这里。</p>

          <p v-if="noticeMessage" class="notice-text">{{ noticeMessage }}</p>

          <section v-if="sources.length" class="sources-box">
            <h4>来源信息</h4>
            <div v-for="source in sources" :key="source.paper_id" class="source-item">
              <strong>{{ source.title }}</strong>
              <span>PDF 摘录：{{ source.has_pdf_excerpt ? `第 ${source.pages.join(", ")} 页` : "未使用" }}</span>
              <span>笔记 {{ source.used_annotations }} 条 · 图表说明 {{ source.used_figures }} 条</span>
            </div>
          </section>

          <section v-if="suggestedQuestions.length" class="suggestion-box">
            <h4>建议继续追问</h4>
            <button
              v-for="question in suggestedQuestions"
              :key="question"
              class="btn-secondary"
              @click="customQuery = question"
            >
              {{ question }}
            </button>
          </section>
        </article>
      </section>
    </section>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { useRoute } from "vue-router";

import {
  fetchAgentTasks,
  fetchPapers,
  fetchProviders,
  runAcademicAgent
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
const answer = ref("");
const sources = ref([]);
const suggestedQuestions = ref([]);
const errorMessage = ref("");
const dataError = ref("");
const noticeMessage = ref("");

const contextOptions = reactive({
  include_metadata: true,
  include_pdf_excerpt: true,
  include_annotations: true,
  include_figures: true
});

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
    ]
      .join(" ")
      .toLowerCase();
    return haystack.includes(keyword);
  });
});

const normalTasks = computed(() => tasks.value.filter((task) => task.key !== "custom_qa"));

const selectedTaskMeta = computed(() => tasks.value.find((task) => task.key === selectedTask.value));

const selectedTaskLabel = computed(() => selectedTaskMeta.value?.label || "尚未选择任务");

const currentTaskHint = computed(() => {
  const task = selectedTaskMeta.value;
  if (!task) return "请选择任务模板。";
  if (task.mode === "single") return "当前任务需要选择 1 篇论文。";
  if (task.mode === "multi") return "当前任务需要选择 2-3 篇论文。";
  return "当前任务需要选择 1-3 篇论文，并填写问题。";
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

function validateBeforeRun(taskKey) {
  const count = selectedPaperIds.value.length;
  const task = tasks.value.find((item) => item.key === taskKey);
  if (!task) return "任务模板不存在。";
  if (task.mode === "single" && count !== 1) return "该任务需要选择 1 篇论文。";
  if (task.mode === "multi" && (count < 2 || count > 3)) return "多篇对比需要选择 2-3 篇论文。";
  if (task.mode === "single_or_multi" && (count < 1 || count > 3)) return "自定义提问需要选择 1-3 篇论文。";
  if (taskKey === "custom_qa" && !customQuery.value.trim()) return "请输入自定义问题。";
  return "";
}

async function runTask(taskKey) {
  selectedTask.value = taskKey;
  noticeMessage.value = "";
  errorMessage.value = "";

  const validationError = validateBeforeRun(taskKey);
  if (validationError) {
    errorMessage.value = validationError;
    return;
  }

  loading.value = true;
  answer.value = "";
  sources.value = [];
  suggestedQuestions.value = [];

  try {
    const result = await runAcademicAgent({
      task: selectedTask.value,
      paper_ids: selectedPaperIds.value,
      query: customQuery.value,
      provider_id: selectedProviderId.value || undefined,
      target_lang: targetLang.value,
      context_options: { ...contextOptions }
    });

    answer.value = result.answer || "";
    sources.value = result.sources || [];
    suggestedQuestions.value = result.suggested_questions || [];
  } catch (error) {
    errorMessage.value = error?.response?.data?.error || "学术 AI 调用失败";
  } finally {
    loading.value = false;
  }
}

async function copyMarkdown() {
  if (!answer.value) return;
  try {
    await navigator.clipboard.writeText(answer.value);
    noticeMessage.value = "Markdown 已复制到剪贴板。";
  } catch {
    noticeMessage.value = "复制失败，请手动选择文本复制。";
  }
}

function clearResult() {
  answer.value = "";
  sources.value = [];
  suggestedQuestions.value = [];
  errorMessage.value = "";
  noticeMessage.value = "";
}

onMounted(loadInitialData);
</script>

<style scoped>
.academic-ai-layout {
  display: grid;
  gap: 1rem;
}

.academic-ai-hero,
.academic-ai-workspace,
.panel-head,
.result-actions {
  display: flex;
  gap: 1rem;
}

.academic-ai-hero {
  align-items: flex-start;
  justify-content: space-between;
}

.academic-ai-hero h2 {
  margin: 0.25rem 0 0.35rem;
  font-family: "Space Grotesk", sans-serif;
}

.academic-ai-hero p,
.panel-head p,
.muted-text {
  margin: 0;
  color: #526b7f;
}

.academic-ai-workspace {
  align-items: flex-start;
}

.paper-picker-panel {
  width: min(390px, 100%);
  flex: 0 0 min(390px, 100%);
}

.task-result-panel {
  flex: 1;
  display: grid;
  gap: 1rem;
  min-width: 0;
}

.panel-head {
  justify-content: space-between;
  align-items: flex-start;
  border-bottom: 1px solid #d8e2ea;
  padding-bottom: 0.7rem;
  margin-bottom: 0.75rem;
}

.panel-head h3 {
  margin: 0;
  font-family: "Space Grotesk", sans-serif;
}

.panel-head p {
  margin-top: 0.2rem;
  font-size: 0.9rem;
}

.paper-search,
.provider-row select,
.target-lang select {
  width: 100%;
  border: 1px solid #cbd9e4;
  border-radius: 10px;
  padding: 0.56rem 0.65rem;
  font: inherit;
  background: #fff;
}

.paper-list {
  margin-top: 0.75rem;
  display: grid;
  gap: 0.6rem;
  max-height: 620px;
  overflow-y: auto;
}

.paper-option {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 0.65rem;
  border: 1px solid #d4dee7;
  border-radius: 12px;
  background: #fff;
  padding: 0.7rem;
  cursor: pointer;
}

.paper-option.selected {
  border-color: #0f6d64;
  background: #eefbf7;
}

.paper-option input {
  margin-top: 0.2rem;
  width: 18px;
  height: 18px;
}

.paper-option h4 {
  margin: 0;
  line-height: 1.35;
}

.paper-option p,
.paper-option span {
  display: block;
  margin: 0.22rem 0 0;
  color: #526b7f;
  font-size: 0.9rem;
}

.tag-row {
  display: flex;
  gap: 0.35rem;
  flex-wrap: wrap;
  margin-top: 0.45rem;
}

.tag-row small {
  border-radius: 999px;
  background: #eef4fa;
  color: #315163;
  padding: 0.12rem 0.45rem;
}

.provider-row {
  display: grid;
  gap: 0.45rem;
}

.provider-row label,
.target-lang,
.custom-qa-box label {
  display: grid;
  gap: 0.35rem;
  color: #33495a;
  font-size: 0.92rem;
  font-weight: 700;
}

.target-lang {
  min-width: 160px;
}

.context-options {
  margin-top: 0.8rem;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.5rem;
}

.context-options label {
  border: 1px solid #d3dee6;
  border-radius: 10px;
  background: #fff;
  padding: 0.5rem 0.6rem;
  color: #30485a;
}

.task-buttons {
  margin-top: 0.85rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.task-buttons button.active {
  background: #0a4f49;
  border-color: #0a4f49;
}

.custom-qa-box {
  margin-top: 0.85rem;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: end;
  gap: 0.6rem;
}

.custom-qa-box textarea {
  min-height: 86px;
  resize: vertical;
}

.result-actions {
  flex-wrap: wrap;
  justify-content: flex-end;
}

.answer-box {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  border: 1px solid #d4dee7;
  border-radius: 12px;
  background: #fbfdff;
  padding: 0.85rem;
  line-height: 1.65;
  font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
}

.loading-text {
  margin: 0;
  color: #145c50;
}

.error-text {
  margin: 0.65rem 0 0;
  color: #9f3a3a;
}

.warning-text,
.notice-text {
  margin: 0.35rem 0 0;
  border-radius: 10px;
  padding: 0.52rem 0.65rem;
}

.warning-text {
  color: #8a5a20;
  background: #fff4d8;
  border: 1px solid #efd79a;
}

.notice-text {
  color: #145c50;
  background: #e5f7f0;
  border: 1px solid #b8e5d7;
}

.sources-box,
.suggestion-box {
  margin-top: 0.95rem;
  border-top: 1px solid #d8e2ea;
  padding-top: 0.75rem;
}

.sources-box h4,
.suggestion-box h4 {
  margin: 0 0 0.55rem;
}

.source-item {
  display: grid;
  gap: 0.16rem;
  border: 1px solid #d4dee7;
  border-radius: 10px;
  background: #fff;
  padding: 0.6rem;
  margin-bottom: 0.5rem;
}

.source-item span {
  color: #526b7f;
  font-size: 0.9rem;
}

.suggestion-box {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}

.suggestion-box h4 {
  width: 100%;
}

button:disabled {
  opacity: 0.58;
  cursor: not-allowed;
}

@media (max-width: 980px) {
  .academic-ai-hero,
  .academic-ai-workspace,
  .custom-qa-box {
    flex-direction: column;
    display: flex;
  }

  .paper-picker-panel {
    width: 100%;
    flex-basis: auto;
  }

  .context-options {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
