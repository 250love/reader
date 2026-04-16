<template>
  <section class="reader-shell" v-if="paper">
    <header class="reader-header">
      <div>
        <p class="brand-kicker">Reader Mode</p>
        <h2>{{ paper.title }}</h2>
        <p>{{ paper.authors || "No authors" }} | {{ paper.conference || "No source" }}</p>
      </div>
    </header>

    <section class="card reader-notes-pane">
      <div class="notes-pane-head">
        <div class="notes-pane-title">
          <h4>高亮笔记</h4>
          <span>{{ highlights.length }} 条</span>
        </div>
        <button class="btn-secondary notes-toggle-btn" @click="notesExpanded = !notesExpanded">
          {{ notesExpanded ? "收起" : "展开" }}
        </button>
      </div>

      <div class="notes-pane-body" :class="{ collapsed: !notesExpanded }">
        <p v-if="annotationError" class="figure-error">{{ annotationError }}</p>
        <p v-if="highlights.length === 0" class="empty-hint">暂无高亮。先选中一句话，再点击“高亮笔记”。</p>

        <article v-for="item in highlights" :key="item.id" class="note-card">
          <header>
            <span>第 {{ item.page || "-" }} 页</span>
            <div class="note-actions">
              <button class="btn-secondary note-mini-btn" @click="locateHighlight(item.id)">定位</button>
              <button class="btn-secondary note-mini-btn" @click="removeHighlight(item.id)">删除</button>
            </div>
          </header>

          <blockquote :style="noteQuoteStyle(item)">
            {{ item.text }}
          </blockquote>

          <div class="note-color-row">
            <button
              v-for="color in highlightPalette"
              :key="`note-${item.id}-${color.id}`"
              class="note-color-btn"
              :class="{ active: item.color === color.id }"
              :style="{ backgroundColor: color.menuColor }"
              :title="color.label"
              @click="setHighlightColor(item, color.id)"
            />
          </div>

          <textarea
            v-model="item.noteDraft"
            rows="4"
            @blur="saveHighlightNote(item)"
            placeholder="在这里写下你的理解、问题或待办..."
          />
        </article>
      </div>
    </section>

    <section class="reader-workspace">
      <article class="card reader-main-pane">
        <div class="reader-main-toolbar">
          <div>
            <h3>PDF 阅读</h3>
            <p class="helper-text">左键框选文本后可直接翻译，或创建高亮笔记（支持多颜色）。</p>
          </div>
          <div class="reader-toolbar-actions">
            <label class="lang-chip">
              目标语言
              <input v-model="targetLang" placeholder="zh-CN" />
            </label>
          </div>
        </div>

        <section class="reader-pdf-pane">
          <div ref="pdfScrollRef" class="reader-canvas-wrap">
            <div ref="pdfPagesRef" class="pdf-pages-host"></div>

            <div v-if="pdfLoading" class="reader-state">正在加载并渲染 PDF...</div>
            <div v-else-if="pdfError" class="reader-state error">{{ pdfError }}</div>
            <div v-else-if="!paper.file_url" class="reader-state">当前文献还没有 PDF 文件。</div>
          </div>
        </section>
      </article>

      <aside class="card reader-translate-pane">
        <div class="reader-side-stack">
          <section class="reader-side-section">
            <div class="translate-pane-head">
              <h3>当前翻译</h3>
            </div>

            <div class="translate-pane-body">
              <p v-if="!currentTranslation" class="empty-hint">暂无翻译。选中文本后点击“翻译”。</p>

              <article v-else class="translate-card">
                <header>
                  <span>第 {{ currentTranslation.page || "-" }} 页</span>
                  <span>{{ currentTranslation.targetLang }}</span>
                </header>
                <p class="source-text">{{ currentTranslation.source }}</p>
                <p class="result-text">{{ currentTranslation.result }}</p>
              </article>
            </div>
          </section>

          <section class="reader-side-section">
            <div class="translate-pane-head">
              <h3>图片面板</h3>
              <span>{{ figureItems.length }} 项</span>
            </div>

            <div class="figure-toolbar">
              <button class="btn-secondary figure-toolbar-btn" @click="loadFigureItems" :disabled="figureLoading">
                刷新
              </button>
              <button class="figure-toolbar-btn" @click="extractFigures" :disabled="figureExtracting">
                {{ figureExtracting ? "抽取中..." : "抽取图片" }}
              </button>
            </div>

            <p v-if="figureLoading" class="empty-hint">正在加载图表...</p>
            <p v-else-if="figureError" class="figure-error">{{ figureError }}</p>
            <p v-else-if="figureItems.length === 0" class="empty-hint">暂无图片，点击“抽取图片”开始。</p>
            <p v-if="!figureLoading && !figureError && figureNotice" class="figure-notice">{{ figureNotice }}</p>

            <div v-if="!figureLoading && !figureError && figureItems.length > 0" class="figure-list">
              <article v-for="item in figureItems" :key="item.id" class="figure-card">
                <button class="figure-preview-btn" @click="jumpToPage(item.page)">
                  <img :src="item.imageUrl" :alt="`figure-${item.id}`" loading="lazy" />
                </button>

                <div class="figure-meta">
                  <div class="figure-meta-row">
                    <span>第 {{ item.page || "-" }} 页 · {{ formatRegionType(item.region_type) }}</span>
                    <button class="btn-secondary note-mini-btn" @click="jumpToPage(item.page)">跳转</button>
                  </div>
                  <textarea
                    v-model="item.noteDraft"
                    rows="3"
                    placeholder="给这个图写图注笔记..."
                  />
                  <button
                    class="btn-secondary figure-save-btn"
                    @click="saveFigureNote(item)"
                    :disabled="savingFigureId === item.id"
                  >
                    {{ savingFigureId === item.id ? "保存中..." : "保存图注" }}
                  </button>
                </div>
              </article>
            </div>
          </section>
        </div>
      </aside>
    </section>

    <div
      v-if="selectionMenu.visible"
      class="selection-menu"
      :style="{ top: `${selectionMenu.top}px`, left: `${selectionMenu.left}px` }"
      @mousedown.prevent
    >
      <div class="selection-color-row">
        <button
          v-for="color in highlightPalette"
          :key="`menu-${color.id}`"
          class="selection-color-btn"
          :class="{ active: activeHighlightColor === color.id }"
          :style="{ backgroundColor: color.menuColor }"
          :title="`高亮颜色：${color.label}`"
          @click="activeHighlightColor = color.id"
        />
      </div>

      <div class="selection-action-row">
        <button @click="translateSelectedText" :disabled="loadingTranslate">
          {{ loadingTranslate ? "翻译中..." : "翻译" }}
        </button>
        <button @click="highlightSelectedText">高亮笔记</button>
      </div>
    </div>
  </section>

  <section class="card" v-else>
    <p>Loading paper...</p>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { GlobalWorkerOptions, TextLayer, getDocument } from "pdfjs-dist/build/pdf.mjs";
import pdfWorkerSrc from "pdfjs-dist/build/pdf.worker.min.mjs?url";

import {
  createPaperAnnotation,
  deletePaperAnnotation,
  extractPaperFigures,
  fetchPaperAnnotations,
  fetchPaperById,
  fetchPaperFigures,
  markPaperOpened,
  translateSelection,
  updatePaperAnnotation,
  updatePaperFigure
} from "@/services/api";

GlobalWorkerOptions.workerSrc = pdfWorkerSrc;

const route = useRoute();

const highlightPalette = [
  {
    id: "yellow",
    label: "黄色",
    menuColor: "#facc15",
    highlightColor: "rgba(250, 204, 21, 0.42)",
    noteBg: "#fff8d8",
    quoteBorder: "#d97706"
  },
  {
    id: "pink",
    label: "粉色",
    menuColor: "#fb7185",
    highlightColor: "rgba(251, 113, 133, 0.33)",
    noteBg: "#ffe5ec",
    quoteBorder: "#e11d48"
  },
  {
    id: "green",
    label: "绿色",
    menuColor: "#4ade80",
    highlightColor: "rgba(74, 222, 128, 0.32)",
    noteBg: "#e8fce8",
    quoteBorder: "#16a34a"
  },
  {
    id: "blue",
    label: "蓝色",
    menuColor: "#38bdf8",
    highlightColor: "rgba(56, 189, 248, 0.33)",
    noteBg: "#e6f6ff",
    quoteBorder: "#0284c7"
  },
  {
    id: "purple",
    label: "紫色",
    menuColor: "#a78bfa",
    highlightColor: "rgba(167, 139, 250, 0.32)",
    noteBg: "#f0ebff",
    quoteBorder: "#7c3aed"
  }
];

const paper = ref(null);
const pdfLoading = ref(false);
const pdfError = ref("");
const loadingTranslate = ref(false);
const targetLang = ref("zh-CN");
const notesExpanded = ref(true);
const activeHighlightColor = ref("yellow");

const pdfScrollRef = ref(null);
const pdfPagesRef = ref(null);

const selectionMenu = reactive({
  visible: false,
  top: 0,
  left: 0
});

const selectionState = reactive({
  text: "",
  page: null,
  rects: []
});

const highlights = ref([]);
const annotationError = ref("");
const currentTranslation = ref(null);
const figureItems = ref([]);
const figureLoading = ref(false);
const figureExtracting = ref(false);
const figureError = ref("");
const figureNotice = ref("");
const savingFigureId = ref("");

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:5000/api/v1";
const backendOrigin = new URL(apiBaseUrl, window.location.origin).origin;

let renderVersion = 0;
let loadingTask = null;
let pdfDoc = null;
let resizeTimer = null;

function getHighlightColor(colorId) {
  return highlightPalette.find((item) => item.id === colorId) || highlightPalette[0];
}

function noteQuoteStyle(item) {
  const color = getHighlightColor(item.color);
  return {
    borderLeftColor: color.quoteBorder,
    backgroundColor: color.noteBg
  };
}

function toAbsoluteUploadUrl(url) {
  if (!url) return "";
  if (/^https?:\/\//i.test(url)) return url;
  return url.startsWith("/") ? `${backendOrigin}${url}` : `${backendOrigin}/${url}`;
}

function normalizeFigureItem(item) {
  const note = typeof item.note === "string" ? item.note : "";
  return {
    ...item,
    imageUrl: toAbsoluteUploadUrl(item.image_url || item.imageUrl || ""),
    noteDraft: note
  };
}

function formatRegionType(regionType) {
  if (regionType === "table") return "表格";
  if (regionType === "boxed_text") return "框选文本";
  if (regionType === "embedded_image") return "图片";
  if (regionType === "ocr_figure") return "OCR 图形";
  return "区域";
}

function clearPdfHost() {
  if (pdfPagesRef.value) {
    pdfPagesRef.value.innerHTML = "";
  }
}

function clearHighlightLayerItems() {
  const host = pdfPagesRef.value;
  if (!host) return;
  host.querySelectorAll(".reader-highlight-item").forEach((el) => el.remove());
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

async function cleanupPdf() {
  renderVersion += 1;
  clearPdfHost();
  try {
    if (loadingTask) {
      await loadingTask.destroy();
    }
  } catch {
    // ignore
  } finally {
    loadingTask = null;
  }

  try {
    if (pdfDoc) {
      await pdfDoc.destroy();
    }
  } catch {
    // ignore
  } finally {
    pdfDoc = null;
  }
}

async function loadPaper() {
  paper.value = await fetchPaperById(route.params.id);
}

function getTargetPageWidth() {
  const host = pdfPagesRef.value;
  if (!host) return 860;
  const width = host.clientWidth;
  const fitted = width - 24;
  const preferred = 860;
  if (fitted >= preferred) {
    return Math.min(fitted, 1200);
  }
  return preferred;
}

function paintHighlights() {
  const host = pdfPagesRef.value;
  if (!host) return;

  clearHighlightLayerItems();

  highlights.value.forEach((item) => {
    const layer = host.querySelector(`.reader-highlight-layer[data-page="${item.page}"]`);
    if (!layer || !Array.isArray(item.rects) || item.rects.length === 0) return;

    const color = getHighlightColor(item.color);
    item.rects.forEach((rect) => {
      if (
        typeof rect.x !== "number" ||
        typeof rect.y !== "number" ||
        typeof rect.w !== "number" ||
        typeof rect.h !== "number"
      ) {
        return;
      }

      const mark = document.createElement("div");
      mark.className = "reader-highlight-item";
      mark.style.left = `${rect.x * 100}%`;
      mark.style.top = `${rect.y * 100}%`;
      mark.style.width = `${rect.w * 100}%`;
      mark.style.height = `${rect.h * 100}%`;
      mark.style.background = color.highlightColor;
      layer.append(mark);
    });
  });
}

async function renderPdf() {
  await cleanupPdf();
  pdfError.value = "";
  if (!paper.value?.file_url) return;

  const host = pdfPagesRef.value;
  if (!host) return;

  pdfLoading.value = true;
  const currentVersion = ++renderVersion;

  try {
    const pdfUrl = toAbsoluteUploadUrl(paper.value.file_url);
    if (!pdfUrl) {
      throw new Error("invalid pdf url");
    }
    loadingTask = getDocument({ url: pdfUrl, withCredentials: true });
    const doc = await loadingTask.promise;
    if (currentVersion !== renderVersion) return;
    pdfDoc = doc;

    const targetWidth = getTargetPageWidth();
    const dpr = window.devicePixelRatio || 1;

    for (let pageNum = 1; pageNum <= doc.numPages; pageNum += 1) {
      if (currentVersion !== renderVersion) return;

      const page = await doc.getPage(pageNum);
      const initialViewport = page.getViewport({ scale: 1 });
      const scale = targetWidth / initialViewport.width;
      const viewport = page.getViewport({ scale });

      const pageWrap = document.createElement("section");
      pageWrap.className = "reader-pdf-page";
      pageWrap.dataset.page = String(pageNum);
      pageWrap.style.width = `${viewport.width}px`;
      pageWrap.style.height = `${viewport.height}px`;

      const canvas = document.createElement("canvas");
      canvas.className = "reader-pdf-canvas";
      canvas.width = Math.floor(viewport.width * dpr);
      canvas.height = Math.floor(viewport.height * dpr);
      canvas.style.width = `${viewport.width}px`;
      canvas.style.height = `${viewport.height}px`;

      const highlightLayer = document.createElement("div");
      highlightLayer.className = "reader-highlight-layer";
      highlightLayer.dataset.page = String(pageNum);
      highlightLayer.style.width = `${viewport.width}px`;
      highlightLayer.style.height = `${viewport.height}px`;

      const textLayerContainer = document.createElement("div");
      textLayerContainer.className = "reader-text-layer textLayer";
      textLayerContainer.style.width = `${viewport.width}px`;
      textLayerContainer.style.height = `${viewport.height}px`;

      pageWrap.append(canvas, highlightLayer, textLayerContainer);
      host.append(pageWrap);

      const ctx = canvas.getContext("2d", { alpha: false });
      if (!ctx) continue;

      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      await page.render({ canvasContext: ctx, viewport }).promise;

      const textContent = await page.getTextContent();
      const textLayer = new TextLayer({
        textContentSource: textContent,
        container: textLayerContainer,
        viewport
      });
      await textLayer.render();
    }

    paintHighlights();
  } catch {
    pdfError.value = "PDF 加载失败，请检查文件是否可访问。";
  } finally {
    if (currentVersion === renderVersion) {
      pdfLoading.value = false;
    }
  }
}

function clearSelection() {
  const selection = window.getSelection();
  if (selection) {
    selection.removeAllRanges();
  }
}

function hideSelectionMenu() {
  selectionMenu.visible = false;
  selectionState.text = "";
  selectionState.page = null;
  selectionState.rects = [];
}

function findPageFromNode(node) {
  let current = node;
  if (current?.nodeType === Node.TEXT_NODE) {
    current = current.parentElement;
  }
  return current?.closest?.(".reader-pdf-page") || null;
}

function collectSelectionRects(range, pageEl) {
  const pageRect = pageEl.getBoundingClientRect();
  const minWidth = 1.5;
  const minHeight = 1.5;

  return Array.from(range.getClientRects())
    .map((rect) => {
      const left = clamp(rect.left - pageRect.left, 0, pageRect.width);
      const top = clamp(rect.top - pageRect.top, 0, pageRect.height);
      const right = clamp(rect.right - pageRect.left, 0, pageRect.width);
      const bottom = clamp(rect.bottom - pageRect.top, 0, pageRect.height);
      const width = right - left;
      const height = bottom - top;
      return { left, top, width, height };
    })
    .filter((rect) => rect.width >= minWidth && rect.height >= minHeight)
    .map((rect) => ({
      x: Number((rect.left / pageRect.width).toFixed(6)),
      y: Number((rect.top / pageRect.height).toFixed(6)),
      w: Number((rect.width / pageRect.width).toFixed(6)),
      h: Number((rect.height / pageRect.height).toFixed(6))
    }));
}

function updateSelectionMenu() {
  const host = pdfPagesRef.value;
  const selection = window.getSelection();
  if (!host || !selection || selection.rangeCount === 0 || selection.isCollapsed) {
    hideSelectionMenu();
    return;
  }

  const range = selection.getRangeAt(0);
  if (!host.contains(range.commonAncestorContainer)) {
    hideSelectionMenu();
    return;
  }

  const startPageEl = findPageFromNode(range.startContainer);
  const endPageEl = findPageFromNode(range.endContainer);
  if (!startPageEl || !endPageEl || startPageEl !== endPageEl) {
    hideSelectionMenu();
    return;
  }

  const text = selection.toString().replace(/\s+/g, " ").trim();
  if (!text) {
    hideSelectionMenu();
    return;
  }

  const rect = range.getBoundingClientRect();
  if (!rect.width && !rect.height) {
    hideSelectionMenu();
    return;
  }

  const page = Number(startPageEl.dataset.page || 0) || null;
  if (!page) {
    hideSelectionMenu();
    return;
  }

  const normalizedRects = collectSelectionRects(range, startPageEl);
  if (normalizedRects.length === 0) {
    hideSelectionMenu();
    return;
  }

  selectionState.text = text;
  selectionState.page = page;
  selectionState.rects = normalizedRects;

  selectionMenu.left = Math.min(Math.max(rect.left + rect.width / 2, 130), window.innerWidth - 130);
  selectionMenu.top = Math.max(rect.top - 74, 10);
  selectionMenu.visible = true;
}

function onDocumentMouseUp() {
  setTimeout(updateSelectionMenu, 20);
}

function onViewportChanged() {
  if (selectionMenu.visible) {
    hideSelectionMenu();
  }
}

function normalizeHighlight(item) {
  const note = typeof item.note === "string" ? item.note : "";
  return {
    id: item.id || "",
    page: Number(item.page || 0) || null,
    text: String(item.text || ""),
    note,
    noteDraft: note,
    color: getHighlightColor(item.color).id,
    rects: Array.isArray(item.rects) ? item.rects : [],
    createdAt: item.created_at || item.createdAt || new Date().toISOString()
  };
}

async function loadSideData() {
  if (!paper.value?.id) return;
  annotationError.value = "";
  try {
    const items = await fetchPaperAnnotations(route.params.id);
    highlights.value = Array.isArray(items) ? items.map(normalizeHighlight) : [];
  } catch (error) {
    highlights.value = [];
    annotationError.value = error?.response?.data?.error || "高亮笔记加载失败，请稍后重试。";
  }
}

async function translateSelectedText() {
  if (!selectionState.text.trim()) return;

  loadingTranslate.value = true;
  try {
    const payload = {
      text: selectionState.text,
      target_lang: targetLang.value || "zh-CN"
    };
    const result = await translateSelection(route.params.id, payload);

    currentTranslation.value = {
      page: selectionState.page,
      source: selectionState.text,
      targetLang: payload.target_lang,
      result: result.translated_text || ""
    };
  } finally {
    loadingTranslate.value = false;
    hideSelectionMenu();
    clearSelection();
  }
}

async function highlightSelectedText() {
  if (!selectionState.text.trim() || !selectionState.page || selectionState.rects.length === 0) return;

  annotationError.value = "";
  try {
    const created = await createPaperAnnotation(route.params.id, {
      page: selectionState.page,
      text: selectionState.text,
      note: "",
      color: activeHighlightColor.value,
      rects: [...selectionState.rects]
    });
    highlights.value.unshift(normalizeHighlight(created));
  } catch (error) {
    annotationError.value = error?.response?.data?.error || "高亮保存失败，请稍后重试。";
  } finally {
    hideSelectionMenu();
    clearSelection();
  }
}

async function setHighlightColor(item, colorId) {
  const nextColor = getHighlightColor(colorId).id;
  if (!item?.id || item.color === nextColor) return;

  annotationError.value = "";
  const prevColor = item.color;
  item.color = nextColor;
  try {
    const updated = await updatePaperAnnotation(route.params.id, item.id, { color: nextColor });
    item.color = getHighlightColor(updated?.color || nextColor).id;
  } catch (error) {
    item.color = prevColor;
    annotationError.value = error?.response?.data?.error || "高亮颜色更新失败。";
  }
}

async function saveHighlightNote(item) {
  if (!item?.id) return;
  const nextNote = typeof item.noteDraft === "string" ? item.noteDraft : "";
  if (nextNote === item.note) return;

  annotationError.value = "";
  const prevNote = item.note;
  item.note = nextNote;
  try {
    const updated = await updatePaperAnnotation(route.params.id, item.id, { note: nextNote });
    item.note = typeof updated?.note === "string" ? updated.note : "";
    item.noteDraft = item.note;
  } catch (error) {
    item.note = prevNote;
    item.noteDraft = prevNote;
    annotationError.value = error?.response?.data?.error || "笔记保存失败。";
  }
}

async function removeHighlight(id) {
  const index = highlights.value.findIndex((item) => item.id === id);
  if (index < 0) return;

  annotationError.value = "";
  const [removed] = highlights.value.splice(index, 1);
  try {
    await deletePaperAnnotation(route.params.id, id);
  } catch (error) {
    highlights.value.splice(index, 0, removed);
    annotationError.value = error?.response?.data?.error || "删除高亮失败。";
  }
}

function locateHighlight(id) {
  const target = highlights.value.find((item) => item.id === id);
  if (!target?.page) return;

  const pageEl = pdfPagesRef.value?.querySelector?.(`.reader-pdf-page[data-page="${target.page}"]`);
  if (pageEl) {
    pageEl.scrollIntoView({ behavior: "smooth", block: "center" });
  }
}

function jumpToPage(page) {
  if (!page) return;
  const pageEl = pdfPagesRef.value?.querySelector?.(`.reader-pdf-page[data-page="${page}"]`);
  if (pageEl) {
    pageEl.scrollIntoView({ behavior: "smooth", block: "center" });
  }
}

async function loadFigureItems() {
  if (!paper.value?.id) return;
  figureLoading.value = true;
  figureError.value = "";
  figureNotice.value = "";
  try {
    const items = await fetchPaperFigures(route.params.id);
    figureItems.value = items.map(normalizeFigureItem);
  } catch (error) {
    figureError.value = error?.response?.data?.error || "图表加载失败，请稍后重试。";
  } finally {
    figureLoading.value = false;
  }
}

async function extractFigures() {
  if (!paper.value?.id) return;
  figureExtracting.value = true;
  figureError.value = "";
  figureNotice.value = "";
  try {
    const data = await extractPaperFigures(route.params.id, {
      simple_mode: true,
      force: true,
      include_tables: false,
      include_boxed_text: false,
      include_embedded_images: true,
      include_image_block_candidates: true,
      include_vector_graphics: true,
      only_captioned_vector_regions: true,
      figure_text_coverage_max: 0.75,
      include_table_text_strategy: false,
      enable_ocr_layout: false,
      ocr_layout_lang: "en",
      ocr_layout_use_gpu: false
    });
    const items = Array.isArray(data?.items) ? data.items : [];
    figureItems.value = items.map(normalizeFigureItem);
    if (Array.isArray(data?.warnings) && data.warnings.length) {
      figureNotice.value = data.warnings.slice(0, 2).join("；");
    }
  } catch (error) {
    figureError.value = error?.response?.data?.error || "图表抽取失败，请检查 PDF 文件。";
  } finally {
    figureExtracting.value = false;
  }
}

async function saveFigureNote(item) {
  if (!paper.value?.id || !item?.id) return;
  savingFigureId.value = item.id;
  figureError.value = "";
  try {
    const updated = await updatePaperFigure(route.params.id, item.id, {
      note: item.noteDraft || ""
    });
    item.note = updated?.note || "";
    item.noteDraft = item.note;
  } catch (error) {
    figureError.value = error?.response?.data?.error || "图注保存失败，请稍后重试。";
  } finally {
    savingFigureId.value = "";
  }
}

function onWindowResize() {
  if (resizeTimer) {
    clearTimeout(resizeTimer);
  }
  resizeTimer = setTimeout(() => {
    if (paper.value?.file_url) {
      renderPdf();
    }
  }, 220);
}

async function openPaper() {
  try {
    await markPaperOpened(route.params.id);
  } catch {
    // ignore if update fails, page can still be opened
  }
  await loadPaper();
}

watch(
  () => paper.value?.id,
  async () => {
    hideSelectionMenu();
    currentTranslation.value = null;
    annotationError.value = "";
    figureError.value = "";
    figureNotice.value = "";
    figureItems.value = [];
    await loadSideData();
    await loadFigureItems();
  }
);

watch(
  () => paper.value?.file_url,
  async () => {
    await nextTick();
    await renderPdf();
  }
);

watch(
  highlights,
  () => {
    paintHighlights();
  },
  { deep: true }
);

watch(
  () => route.params.id,
  async () => {
    await openPaper();
  }
);

onMounted(async () => {
  document.addEventListener("mouseup", onDocumentMouseUp);
  window.addEventListener("scroll", onViewportChanged, true);
  window.addEventListener("resize", onWindowResize);
  await openPaper();
});

onBeforeUnmount(() => {
  document.removeEventListener("mouseup", onDocumentMouseUp);
  window.removeEventListener("scroll", onViewportChanged, true);
  window.removeEventListener("resize", onWindowResize);
  if (resizeTimer) {
    clearTimeout(resizeTimer);
    resizeTimer = null;
  }
  clearSelection();
  hideSelectionMenu();
  cleanupPdf();
});
</script>

<style scoped>
.reader-shell {
  display: grid;
  gap: 0.95rem;
}

.reader-notes-pane {
  padding: 0.72rem;
  border: 1px solid #ced9e2;
  border-radius: 14px;
  background: linear-gradient(180deg, #fbfdff 0%, #f3f8fc 100%);
}

.notes-pane-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 0.08rem 0.55rem;
  border-bottom: 1px solid #d5e0e8;
}

.notes-pane-title {
  display: flex;
  align-items: center;
  gap: 0.55rem;
}

.notes-pane-head h4 {
  margin: 0;
  font-size: 1rem;
  color: #234055;
}

.notes-pane-head span {
  color: #4b677c;
  font-size: 0.86rem;
  font-weight: 700;
}

.notes-toggle-btn {
  padding: 0.22rem 0.52rem;
  border-radius: 8px;
  font-size: 0.8rem;
  line-height: 1.2;
}

.notes-pane-body {
  margin-top: 0.65rem;
  max-height: 280px;
  min-height: 140px;
  overflow: auto;
  display: grid;
  gap: 0.6rem;
  resize: vertical;
  transition: max-height 0.24s ease, opacity 0.2s ease, margin-top 0.2s ease, min-height 0.2s ease;
}

.notes-pane-body.collapsed {
  margin-top: 0;
  max-height: 0;
  min-height: 0;
  opacity: 0;
  overflow: hidden;
  resize: none;
  pointer-events: none;
}

.reader-workspace {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 560px;
  gap: 1rem;
}

.reader-main-pane {
  padding: 0.75rem;
  min-height: 84vh;
}

.reader-main-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.8rem;
  padding: 0.15rem 0.25rem 0.65rem;
  border-bottom: 1px solid #d9e2ea;
}

.reader-main-toolbar h3 {
  margin: 0;
  font-family: "Space Grotesk", sans-serif;
}

.reader-toolbar-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.lang-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.38rem 0.5rem;
  border: 1px solid #c9d8e1;
  border-radius: 999px;
  color: #2f4658;
  font-size: 0.86rem;
  background: linear-gradient(180deg, #fff 0%, #f5fbfe 100%);
}

.lang-chip input {
  width: 84px;
  border: 0;
  background: transparent;
  font: inherit;
  color: #21394c;
  outline: none;
}

.reader-pdf-pane {
  min-width: 0;
  margin-top: 0.7rem;
}

.reader-canvas-wrap {
  position: relative;
  min-height: 74vh;
  max-height: calc(100vh - 220px);
  overflow: auto;
  border-radius: 14px;
  border: 1px solid #cfdae3;
  background: linear-gradient(180deg, #f8fbfd 0%, #f1f6fb 100%);
  padding: 0.72rem;
}

.pdf-pages-host {
  display: grid;
  justify-content: center;
  gap: 0.9rem;
  width: max-content;
  min-width: 100%;
  margin: 0 auto;
}

.reader-state {
  display: grid;
  place-items: center;
  min-height: 260px;
  color: #486277;
}

.reader-state.error {
  color: #9f3a3a;
}

.reader-translate-pane {
  padding: 0.8rem;
  min-height: 84vh;
  max-height: calc(100vh - 172px);
  overflow: auto;
}

.reader-side-stack {
  display: grid;
  gap: 0.95rem;
}

.reader-side-section {
  border: 1px solid #d4dee6;
  border-radius: 12px;
  background: linear-gradient(180deg, #fbfdff 0%, #f4f9fc 100%);
  padding: 0.7rem;
}

.translate-pane-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #d8e2ea;
  padding-bottom: 0.55rem;
}

.translate-pane-head h3 {
  margin: 0;
  font-family: "Space Grotesk", sans-serif;
}

.translate-pane-head span {
  color: #4d687e;
  font-size: 0.86rem;
  font-weight: 700;
}

.translate-pane-body {
  margin-top: 0.7rem;
  display: grid;
  gap: 0.62rem;
}

.figure-toolbar {
  margin-top: 0.65rem;
  display: flex;
  gap: 0.45rem;
}

.figure-toolbar-btn {
  padding: 0.36rem 0.65rem;
  border-radius: 8px;
  font-size: 0.82rem;
}

.figure-error {
  margin: 0.5rem 0 0;
  color: #9f3a3a;
  font-size: 0.88rem;
}

.figure-notice {
  margin: 0.5rem 0 0;
  color: #7a5b1d;
  background: #fff7e0;
  border: 1px solid #edd8a3;
  border-radius: 8px;
  padding: 0.35rem 0.48rem;
  font-size: 0.82rem;
}

.figure-list {
  margin-top: 0.65rem;
  display: grid;
  gap: 0.65rem;
}

.figure-card {
  border: 1px solid #d0dbe4;
  border-radius: 12px;
  background: #fff;
  padding: 0.55rem;
  display: grid;
  gap: 0.5rem;
}

.figure-preview-btn {
  width: 100%;
  border: 1px solid #d4dee7;
  border-radius: 10px;
  padding: 0;
  background: #f4f8fb;
  overflow: hidden;
}

.figure-preview-btn img {
  display: block;
  width: 100%;
  max-height: 180px;
  object-fit: contain;
  background: #fff;
}

.figure-meta {
  display: grid;
  gap: 0.44rem;
}

.figure-meta-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #446277;
  font-size: 0.82rem;
  font-weight: 700;
}

.figure-meta textarea {
  width: 100%;
  border: 1px solid #c9d8e1;
  border-radius: 8px;
  padding: 0.45rem 0.55rem;
  font: inherit;
  background: #fff;
  resize: vertical;
}

.figure-save-btn {
  justify-self: end;
  font-size: 0.8rem;
  padding: 0.24rem 0.52rem;
}

.empty-hint {
  margin: 0.2rem 0;
  color: #537088;
  font-size: 0.9rem;
}

.note-card,
.translate-card {
  border: 1px solid #d0dbe4;
  border-radius: 14px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fcff 100%);
  padding: 0.62rem;
  display: grid;
  gap: 0.45rem;
}

.note-card header,
.translate-card header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #446277;
  font-size: 0.82rem;
  font-weight: 700;
}

.note-actions {
  display: flex;
  gap: 0.35rem;
}

.note-mini-btn {
  padding: 0.18rem 0.46rem;
  border-radius: 7px;
  font-size: 0.76rem;
}

.note-card blockquote {
  margin: 0;
  border-left: 4px solid #6366f1;
  border-radius: 8px;
  padding: 0.52rem 0.56rem;
  color: #223849;
  line-height: 1.42;
}

.note-color-row {
  display: flex;
  align-items: center;
  gap: 0.42rem;
}

.note-color-btn {
  width: 18px;
  height: 18px;
  border: 1px solid rgba(51, 65, 85, 0.32);
  border-radius: 999px;
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.88) inset;
}

.note-color-btn.active {
  transform: scale(1.06);
  border-color: rgba(15, 23, 42, 0.92);
}

.note-card textarea {
  width: 100%;
  border: 1px solid #c9d8e1;
  border-radius: 9px;
  padding: 0.5rem 0.6rem;
  font: inherit;
  background: #fff;
  resize: vertical;
}

.translate-card .source-text {
  margin: 0;
  color: #2b4255;
  font-size: 0.92rem;
}

.translate-card .result-text {
  margin: 0;
  color: #183d35;
  background: #e9f7f1;
  border-radius: 9px;
  padding: 0.5rem 0.56rem;
  line-height: 1.42;
}

.selection-menu {
  position: fixed;
  z-index: 1200;
  transform: translateX(-50%);
  border: 1px solid #ccd8e2;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 14px 28px rgba(15, 30, 45, 0.2);
  padding: 0.35rem;
  display: grid;
  gap: 0.32rem;
}

.selection-color-row {
  display: flex;
  gap: 0.42rem;
  padding: 0.08rem 0.08rem 0;
}

.selection-color-btn {
  width: 24px;
  height: 24px;
  border: 1px solid rgba(51, 65, 85, 0.35);
  border-radius: 8px;
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.9) inset;
}

.selection-color-btn.active {
  transform: translateY(-1px);
  border-color: rgba(15, 23, 42, 0.96);
}

.selection-action-row {
  display: flex;
  gap: 0.32rem;
}

.selection-action-row button {
  border-radius: 8px;
  padding: 0.38rem 0.68rem;
  font-size: 0.85rem;
}

:deep(.reader-pdf-page) {
  position: relative;
  border-radius: 10px;
  overflow: hidden;
  box-shadow: 0 8px 20px rgba(46, 67, 88, 0.15);
  background: #fff;
}

:deep(.reader-pdf-canvas) {
  display: block;
  width: 100%;
  height: 100%;
}

:deep(.reader-highlight-layer) {
  position: absolute;
  inset: 0;
  z-index: 1;
  pointer-events: none;
}

:deep(.reader-highlight-item) {
  position: absolute;
  border-radius: 3px;
}

:deep(.reader-text-layer) {
  position: absolute;
  inset: 0;
  overflow: hidden;
  line-height: 1;
  text-size-adjust: none;
  z-index: 2;
}

:deep(.reader-text-layer span),
:deep(.reader-text-layer br) {
  color: transparent;
  position: absolute;
  white-space: pre;
  cursor: text;
  transform-origin: 0 0;
}

:deep(.reader-text-layer span::selection) {
  background: rgba(94, 129, 255, 0.34);
}

@media (max-width: 1480px) {
  .reader-workspace {
    grid-template-columns: minmax(0, 1fr) 500px;
  }
}

@media (max-width: 1200px) {
  .reader-workspace {
    grid-template-columns: 1fr;
  }

  .reader-translate-pane {
    max-height: none;
    min-height: auto;
  }
}

@media (max-width: 980px) {
  .notes-pane-body {
    max-height: none;
  }

  .reader-canvas-wrap {
    max-height: 70vh;
  }
}
</style>



