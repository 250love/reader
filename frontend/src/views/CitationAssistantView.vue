<template>
  <section class="citation-layout">
    <header class="citation-header">
      <div>
        <p class="brand-kicker">Citation Assistant</p>
        <h2>引用助手</h2>
        <p>选择已导入文献，优先使用 PDF 自动识别信息生成规范引用。</p>
      </div>

      <div class="citation-controls">
        <label class="format-control">
          引用格式
          <select v-model="citationFormat">
            <option value="GBT7714">GB/T 7714</option>
            <option value="APA">APA</option>
            <option value="IEEE">IEEE</option>
          </select>
        </label>
        <button class="btn-secondary" @click="toggleSelectAll" :disabled="papers.length === 0">
          {{ allSelected ? "取消全选" : "全选" }}
        </button>
        <button @click="onGenerateCitations" :disabled="generating || selectedIds.length === 0">
          {{ generating ? "生成中..." : "生成引用" }}
        </button>
      </div>
    </header>

    <section class="citation-workspace">
      <article class="card citation-paper-panel">
        <div class="panel-head">
          <div>
            <h3>选择文献</h3>
            <p>{{ selectedIds.length }} / {{ papers.length }} 篇已选</p>
          </div>
          <button class="btn-secondary" @click="loadPapers" :disabled="loading">
            {{ loading ? "刷新中..." : "刷新" }}
          </button>
        </div>

        <p v-if="loading" class="empty-hint">正在加载文献...</p>
        <p v-else-if="errorMsg" class="error-text">{{ errorMsg }}</p>
        <p v-else-if="papers.length === 0" class="empty-hint">暂无文献，请先在文献库导入 PDF。</p>

        <div v-else class="citation-paper-list">
          <label
            v-for="paper in papers"
            :key="paper.id"
            :class="['citation-paper-card', { selected: selectedIdSet.has(paper.id) }]"
          >
            <input
              type="checkbox"
              :checked="selectedIdSet.has(paper.id)"
              @change="togglePaper(paper.id)"
            />
            <div>
              <div class="paper-card-title-row">
                <h4>{{ paper.title }}</h4>
                <span :class="['metadata-pill', { ready: hasCitationMetadata(paper) }]">
                  {{ hasCitationMetadata(paper) ? "已识别" : "待补全" }}
                </span>
              </div>
              <p>{{ paper.authors || "未知作者" }}</p>
              <span>{{ paper.conference || "未填写来源" }} · {{ paper.year || "n.d." }}</span>
              <div class="paper-card-actions" @click.stop>
                <button class="btn-secondary" @click="startEditMetadata(paper)">编辑引用信息</button>
                <button class="btn-secondary" @click="onExtractMetadata(paper)" :disabled="extractingId === paper.id">
                  {{ extractingId === paper.id ? "识别中..." : "自动识别信息" }}
                </button>
              </div>
            </div>
          </label>
        </div>

        <section v-if="editingPaperId" class="metadata-editor">
          <div class="panel-head compact">
            <div>
              <h3>编辑引用信息</h3>
              <p>缺失字段可手动补全，保存后引用生成会优先使用这里的信息。</p>
            </div>
            <button class="btn-secondary" @click="cancelEditMetadata">关闭</button>
          </div>

          <div class="metadata-grid">
            <label>标题<input v-model="metadataForm.title" /></label>
            <label>作者（用逗号分隔）<input v-model="metadataAuthorsText" /></label>
            <label>年份<input v-model="metadataForm.year" /></label>
            <label>来源 / 期刊 / 会议<input v-model="metadataForm.venue" /></label>
            <label>卷号<input v-model="metadataForm.volume" /></label>
            <label>期号<input v-model="metadataForm.issue" /></label>
            <label>页码<input v-model="metadataForm.pages" /></label>
            <label>DOI<input v-model="metadataForm.doi" /></label>
            <label>arXiv 编号<input v-model="metadataForm.arxivId" /></label>
            <label>URL<input v-model="metadataForm.url" /></label>
          </div>

          <label class="metadata-citation-text">
            原始引用格式（GB/T 7714 优先使用）
            <textarea v-model="metadataForm.citationText" rows="3" />
          </label>

          <button @click="saveMetadata" :disabled="savingMetadata">
            {{ savingMetadata ? "保存中..." : "保存引用信息" }}
          </button>
        </section>
      </article>

      <aside class="card citation-output-panel">
        <div class="panel-head">
          <div>
            <h3>生成结果</h3>
            <p>{{ displayFormat }} · {{ citationItems.length }} 条</p>
          </div>
          <button class="btn-secondary" @click="copyAllCitations" :disabled="!citationText">
            复制全部引用
          </button>
        </div>

        <div v-if="citationItems.length > 0" class="citation-result-list">
          <article v-for="item in citationItems" :key="item.paper_id" class="citation-result-card">
            <p>{{ item.citation }}</p>
            <button class="btn-secondary" @click="copyOneCitation(item.citation)">复制单条引用</button>
          </article>
        </div>

        <textarea
          v-model="citationText"
          readonly
          placeholder="选择文献并点击“生成引用”，结果会显示在这里。"
        />

        <p v-if="noticeMsg" class="notice-text">{{ noticeMsg }}</p>
      </aside>
    </section>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";

import {
  extractPaperCitationMetadata,
  fetchPapers,
  generatePaperCitations,
  updatePaperCitationMetadata
} from "@/services/api";

const emptyMetadata = {
  title: "",
  authors: [],
  year: "",
  venue: "",
  volume: "",
  issue: "",
  pages: "",
  doi: "",
  arxivId: "",
  url: "",
  citationText: "",
  source: "manual"
};

const papers = ref([]);
const selectedIds = ref([]);
const citationFormat = ref("GBT7714");
const citationText = ref("");
const citationItems = ref([]);
const displayFormat = ref("GB/T 7714");
const loading = ref(false);
const generating = ref(false);
const extractingId = ref("");
const savingMetadata = ref(false);
const editingPaperId = ref("");
const metadataAuthorsText = ref("");
const errorMsg = ref("");
const noticeMsg = ref("");

const metadataForm = reactive({ ...emptyMetadata });

const selectedIdSet = computed(() => new Set(selectedIds.value));
const allSelected = computed(() => papers.value.length > 0 && selectedIds.value.length === papers.value.length);

async function loadPapers() {
  loading.value = true;
  errorMsg.value = "";
  noticeMsg.value = "";
  try {
    papers.value = await fetchPapers({ sort_by: "last_opened_at", sort_order: "desc" });
    const availableIds = new Set(papers.value.map((paper) => paper.id));
    selectedIds.value = selectedIds.value.filter((id) => availableIds.has(id));
  } catch (error) {
    papers.value = [];
    errorMsg.value = error?.response?.data?.error || "文献加载失败，请稍后重试。";
  } finally {
    loading.value = false;
  }
}

function hasCitationMetadata(paper) {
  const metadata = paper?.citationMetadata || {};
  return Boolean(
    metadata.title ||
      metadata.authors?.length ||
      metadata.year ||
      metadata.venue ||
      metadata.doi ||
      metadata.arxivId ||
      metadata.citationText
  );
}

function togglePaper(paperId) {
  if (selectedIdSet.value.has(paperId)) {
    selectedIds.value = selectedIds.value.filter((id) => id !== paperId);
    return;
  }
  selectedIds.value = [...selectedIds.value, paperId];
}

function toggleSelectAll() {
  selectedIds.value = allSelected.value ? [] : papers.value.map((paper) => paper.id);
}

function startEditMetadata(paper) {
  const metadata = { ...emptyMetadata, ...(paper.citationMetadata || {}) };
  editingPaperId.value = paper.id;
  Object.assign(metadataForm, metadata);
  metadataAuthorsText.value = Array.isArray(metadata.authors) ? metadata.authors.join(", ") : "";
}

function cancelEditMetadata() {
  editingPaperId.value = "";
}

async function onExtractMetadata(paper) {
  if (!paper?.id || extractingId.value) return;
  extractingId.value = paper.id;
  errorMsg.value = "";
  noticeMsg.value = "";
  try {
    const metadata = await extractPaperCitationMetadata(paper.id);
    noticeMsg.value = "已从 PDF 前几页尝试识别引用信息。";
    if (editingPaperId.value === paper.id) {
      Object.assign(metadataForm, { ...emptyMetadata, ...metadata });
      metadataAuthorsText.value = Array.isArray(metadata.authors) ? metadata.authors.join(", ") : "";
    }
    await loadPapers();
  } catch (error) {
    errorMsg.value = error?.response?.data?.error || "PDF 引用信息识别失败。";
  } finally {
    extractingId.value = "";
  }
}

async function saveMetadata() {
  if (!editingPaperId.value) return;
  savingMetadata.value = true;
  errorMsg.value = "";
  noticeMsg.value = "";
  try {
    const payload = {
      ...metadataForm,
      authors: metadataAuthorsText.value
        .split(/[,，;；、]/)
        .map((item) => item.trim())
        .filter(Boolean),
      source: "manual"
    };
    await updatePaperCitationMetadata(editingPaperId.value, payload);
    noticeMsg.value = "引用信息已保存。";
    await loadPapers();
  } catch (error) {
    errorMsg.value = error?.response?.data?.error || "引用信息保存失败。";
  } finally {
    savingMetadata.value = false;
  }
}

async function onGenerateCitations() {
  if (selectedIds.value.length === 0) return;

  generating.value = true;
  errorMsg.value = "";
  noticeMsg.value = "";
  try {
    const result = await generatePaperCitations({
      paper_ids: selectedIds.value,
      format: citationFormat.value
    });
    citationItems.value = Array.isArray(result.items) ? result.items : [];
    citationText.value = result.text || "";
    displayFormat.value = result.format || citationFormat.value;
    noticeMsg.value = `已生成 ${citationItems.value.length} 条 ${displayFormat.value} 引用。`;
  } catch (error) {
    citationItems.value = [];
    citationText.value = "";
    errorMsg.value = error?.response?.data?.error || "引用生成失败，请稍后重试。";
  } finally {
    generating.value = false;
  }
}

async function copyText(text, successMessage) {
  if (!text) return;

  try {
    await navigator.clipboard.writeText(text);
    noticeMsg.value = successMessage;
  } catch {
    noticeMsg.value = "复制失败，请手动选中文本复制。";
  }
}

function copyOneCitation(citation) {
  copyText(citation, "单条引用已复制到剪贴板。");
}

function copyAllCitations() {
  copyText(citationText.value, "全部引用已复制到剪贴板。");
}

onMounted(loadPapers);
</script>

<style scoped>
.citation-layout {
  display: grid;
  gap: 1rem;
}

.citation-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
}

.citation-header h2 {
  margin: 0.25rem 0 0.35rem;
  font-family: "Space Grotesk", sans-serif;
}

.citation-header p {
  margin: 0;
  color: #526b7f;
}

.citation-controls {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 0.55rem;
}

.format-control {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  border: 1px solid #cbd9e4;
  border-radius: 999px;
  background: #fff;
  padding: 0.38rem 0.58rem;
  color: #2d4658;
  font-weight: 700;
  font-size: 0.9rem;
}

.format-control select {
  border: 0;
  background: transparent;
  color: #1f3648;
  font: inherit;
  outline: none;
}

.citation-workspace {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(400px, 0.8fr);
  gap: 1rem;
}

.citation-paper-panel,
.citation-output-panel {
  padding: 0.9rem;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.75rem;
  border-bottom: 1px solid #d8e2ea;
  padding-bottom: 0.7rem;
  margin-bottom: 0.75rem;
}

.panel-head.compact {
  margin-bottom: 0.7rem;
}

.panel-head h3 {
  margin: 0;
  font-family: "Space Grotesk", sans-serif;
}

.panel-head p {
  margin: 0.18rem 0 0;
  color: #587184;
  font-size: 0.88rem;
}

.citation-paper-list,
.citation-result-list {
  display: grid;
  gap: 0.62rem;
}

.citation-paper-card {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 0.68rem;
  align-items: flex-start;
  border: 1px solid #d4dee7;
  border-radius: 12px;
  background: #fff;
  padding: 0.72rem;
  cursor: pointer;
}

.citation-paper-card.selected {
  border-color: #0f6d64;
  background: #eefbf7;
}

.citation-paper-card input {
  margin-top: 0.2rem;
  width: 18px;
  height: 18px;
}

.paper-card-title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.6rem;
}

.metadata-pill {
  flex: 0 0 auto;
  color: #8a5a20;
  background: #fff4d8;
  border: 1px solid #efd79a;
  border-radius: 999px;
  padding: 0.12rem 0.45rem;
  font-size: 0.72rem;
  font-weight: 700;
}

.metadata-pill.ready {
  color: #145c50;
  background: #e4f7f0;
  border-color: #b8e5d7;
}

.citation-paper-card h4 {
  margin: 0;
  color: #1f3445;
  line-height: 1.3;
}

.citation-paper-card p {
  margin: 0.28rem 0 0.2rem;
  color: #496478;
}

.citation-paper-card span {
  color: #6a7d8e;
  font-size: 0.86rem;
}

.paper-card-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  margin-top: 0.55rem;
}

.paper-card-actions button,
.citation-result-card button {
  border-radius: 8px;
  padding: 0.28rem 0.58rem;
  font-size: 0.82rem;
}

.metadata-editor {
  margin-top: 0.9rem;
  border: 1px solid #d4dee7;
  border-radius: 12px;
  background: #fbfdff;
  padding: 0.78rem;
}

.metadata-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.62rem;
}

.metadata-grid label,
.metadata-citation-text {
  display: grid;
  gap: 0.28rem;
  color: #3b5265;
  font-size: 0.86rem;
  font-weight: 700;
}

.metadata-grid input,
.metadata-citation-text textarea {
  width: 100%;
  border: 1px solid #cbd9e4;
  border-radius: 9px;
  padding: 0.48rem 0.58rem;
  font: inherit;
  background: #fff;
}

.metadata-citation-text {
  margin: 0.62rem 0;
}

.citation-result-card {
  display: grid;
  gap: 0.5rem;
  border: 1px solid #d4dee7;
  border-radius: 12px;
  background: #fff;
  padding: 0.68rem;
}

.citation-result-card p {
  margin: 0;
  color: #263a4b;
  line-height: 1.55;
}

.citation-result-card button {
  justify-self: start;
}

.citation-output-panel textarea {
  width: 100%;
  min-height: 220px;
  margin-top: 0.72rem;
  border: 1px solid #cbd9e4;
  border-radius: 12px;
  padding: 0.78rem;
  font: inherit;
  line-height: 1.55;
  resize: vertical;
  background: #fbfdff;
}

.empty-hint {
  margin: 0;
  color: #537088;
}

.error-text {
  margin: 0;
  color: #9f3a3a;
}

.notice-text {
  margin: 0.65rem 0 0;
  color: #145c50;
  background: #e5f7f0;
  border: 1px solid #b8e5d7;
  border-radius: 10px;
  padding: 0.5rem 0.62rem;
}

:global(html[data-theme="dark"]) .citation-header p,
:global(html[data-theme="dark"]) .panel-head p,
:global(html[data-theme="dark"]) .citation-paper-card p,
:global(html[data-theme="dark"]) .citation-paper-card span,
:global(html[data-theme="dark"]) .empty-hint {
  color: var(--muted);
}

:global(html[data-theme="dark"]) .format-control,
:global(html[data-theme="dark"]) .citation-paper-card,
:global(html[data-theme="dark"]) .metadata-editor,
:global(html[data-theme="dark"]) .citation-result-card {
  background: var(--surface-soft);
  border-color: var(--line);
  color: var(--text);
}

:global(html[data-theme="dark"]) .format-control select,
:global(html[data-theme="dark"]) .citation-paper-card h4,
:global(html[data-theme="dark"]) .citation-result-card p,
:global(html[data-theme="dark"]) .metadata-grid label,
:global(html[data-theme="dark"]) .metadata-citation-text {
  color: var(--text);
}

:global(html[data-theme="dark"]) .panel-head {
  border-color: var(--line);
}

:global(html[data-theme="dark"]) .citation-paper-card.selected {
  border-color: var(--primary-soft-border);
  background: var(--primary-soft);
}

:global(html[data-theme="dark"]) .metadata-pill {
  background: rgba(251, 191, 36, 0.12);
  border-color: rgba(251, 191, 36, 0.28);
  color: #facc15;
}

:global(html[data-theme="dark"]) .metadata-pill.ready,
:global(html[data-theme="dark"]) .notice-text {
  background: var(--primary-soft);
  border-color: var(--primary-soft-border);
  color: var(--primary);
}

:global(html[data-theme="dark"]) .error-text {
  color: var(--danger);
}

:global(html[data-theme="dark"]) .citation-output-panel textarea {
  background: #0f172a;
  border-color: var(--line);
  color: var(--text);
}

@media (max-width: 980px) {
  .citation-header {
    flex-direction: column;
  }

  .citation-controls {
    justify-content: flex-start;
  }

  .citation-workspace,
  .metadata-grid {
    grid-template-columns: 1fr;
  }
}
</style>
