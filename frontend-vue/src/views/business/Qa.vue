<!-- P7b.3 答疑页：讲师提问 + A4/RAG 带引用回答 + 未命中/低置信转人工 -->
<template>
  <div class="business">
    <header class="biz-header">
      <el-button link @click="$router.push('/portal')"><el-icon><Back /></el-icon> 工作台</el-button>
      <div class="biz-title">智能答疑</div>
    </header>
    <main class="biz-main">
      <el-card shadow="never" class="panel">
        <div class="ask-bar">
          <el-input v-model="question" placeholder="输入你的问题，例如：什么是Agent？" @keyup.enter="ask" />
          <el-button type="primary" :loading="asking" @click="ask">提问</el-button>
        </div>
        <div v-loading="asking" style="min-height:80px">
          <div v-for="(qa,i) in history" :key="i" class="qa-item">
            <div class="qa-q">Q：{{ qa.question }}</div>
            <div class="qa-a" v-if="qa.needs_human">
              <el-alert title="该问题知识库未命中/置信度低，已转人工或技术处理" type="warning" :closable="false" />
              <div class="source-row" v-if="qa.answer">建议：{{ qa.answer }}</div>
            </div>
            <div class="qa-a" v-else>A：{{ qa.answer }}</div>
            <div class="source-row" v-if="!qa.needs_human && qa.source">
              引用来源：<el-tag size="small" type="info">{{ qa.source }}</el-tag>
            </div>
          </div>
          <el-empty v-if="!asking && history.length===0" description="提问后将展示 AI 回答（带知识库引用）" />
        </div>
      </el-card>
    </main>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api/client'
const question = ref('')
const asking = ref(false)
const history = ref<any[]>([])
async function ask() {
  const q = question.value.trim()
  if (!q) { ElMessage.warning('请输入问题'); return }
  asking.value = true
  try {
    const r = await api.post('/qa/ask', { question: q })
    history.value.unshift({ question: q, ...r.data })
    question.value = ''
  } catch (e:any) {
    ElMessage.error(e?.response?.data?.detail || '提问失败')
  } finally { asking.value = false }
}
onMounted(() => {})
</script>

<style scoped>
.business { min-height: 100vh; background: #f5f7fa; }
.biz-header { display: flex; align-items: center; gap: 16px; padding: 16px 24px; background: #fff; border-bottom: 1px solid #e6e8eb; }
.biz-title { font-size: 18px; font-weight: 600; color: #1f2329; flex: 1; }
.biz-main { max-width: 860px; margin: 0 auto; padding: 24px; }
.panel { border-radius: 10px; }
.qa-item { padding: 14px; border-bottom: 1px solid #f0f0f0; }
.qa-q { font-weight: 600; color: #1f2329; }
.qa-a { margin-top: 8px; color: #333; }
.source-row { margin-top: 8px; font-size: 12px; color: #888; }
.ask-bar { display: flex; gap: 10px; margin-bottom: 18px; }
</style>
