<!-- P2.5 管理后台：组织管理(建组/派组长) + 子系统注册(增/停/激活) -->
<template>
  <div class="admin">
    <header class="admin-header">
      <el-button link @click="$router.push('/portal')"><el-icon><Back /></el-icon> 工作台</el-button>
      <div class="admin-title">管理后台</div>
    </header>

    <main class="admin-main">
      <!-- 组织管理 -->
      <el-card shadow="never" class="panel">
        <template #header>
          <div class="panel-head">
            <span class="panel-title">业务组</span>
            <el-button type="primary" size="small" @click="openCreateGroup">新建组</el-button>
          </div>
        </template>
        <el-table :data="groups" border>
          <el-table-column prop="name" label="组名" />
          <el-table-column label="组长">
            <template #default="{ row }">
              {{ leaderName(row) || '未指派' }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="140">
            <template #default="{ row }">
              <el-button size="small" @click="openAssignLeader(row)">指派组长</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 子系统注册 -->
      <el-card shadow="never" class="panel">
        <template #header>
          <div class="panel-head">
            <span class="panel-title">子系统注册</span>
            <el-button type="primary" size="small" @click="openCreateSubsys">注册子系统</el-button>
          </div>
        </template>
        <el-table :data="subsystems" border>
          <el-table-column prop="name" label="名称" />
          <el-table-column prop="key" label="标识" />
          <el-table-column prop="url" label="接入地址" />
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="statusType(row.status)">{{ statusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="180">
            <template #default="{ row }">
              <el-button v-if="row.status !== 'active'" size="small" type="success" @click="setStatus(row, 'active')">激活</el-button>
              <el-button v-if="row.status === 'active'" size="small" type="warning" @click="setStatus(row, 'stopped')">停用</el-button>
              <el-button size="small" type="danger" plain @click="setStatus(row, 'archived')">下线</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </main>

    <el-dialog v-model="groupDlg.show" title="新建业务组" width="420px">
      <el-form label-width="70px">
        <el-form-item label="组名"><el-input v-model="groupDlg.name" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="groupDlg.show = false">取消</el-button>
        <el-button type="primary" @click="createGroup">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="leaderDlg.show" title="指派组长" width="420px">
      <el-form label-width="70px">
        <el-form-item label="组长">
          <el-select v-model="leaderDlg.userId" placeholder="选择组长">
            <el-option v-for="u in leaders" :key="u.id" :label="u.display_name || u.username" :value="u.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="leaderDlg.show = false">取消</el-button>
        <el-button type="primary" @click="assignLeader">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="subsysDlg.show" title="注册子系统" width="460px">
      <el-form label-width="80px">
        <el-form-item label="名称"><el-input v-model="subsysDlg.name" /></el-form-item>
        <el-form-item label="标识"><el-input v-model="subsysDlg.key" placeholder="如 collab" /></el-form-item>
        <el-form-item label="接入地址"><el-input v-model="subsysDlg.url" placeholder="http://..." /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="subsysDlg.show = false">取消</el-button>
        <el-button type="primary" @click="createSubsys">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import api from '../api/client'

const groups = ref<any[]>([])
const subsystems = ref<any[]>([])
const leaders = ref<any[]>([])

const groupDlg = reactive({ show: false, name: '' })
const leaderDlg = reactive({ show: false, groupId: 0, userId: 0 })
const subsysDlg = reactive({ show: false, name: '', key: '', url: '' })

async function loadAll() {
  const [g, s] = await Promise.all([
    api.get('/org/groups'),
    api.get('/subsystems'),
  ])
  groups.value = g.data
  subsystems.value = s.data
}

async function loadLeaders() {
  const r = await api.get('/org/users?role=leader')
  leaders.value = r.data
}

function openCreateGroup() { groupDlg.show = true; groupDlg.name = '' }
async function createGroup() {
  await api.post('/org/groups', { name: groupDlg.name })
  groupDlg.show = false
  await loadAll()
}

function openAssignLeader(row: any) { leaderDlg.show = true; leaderDlg.groupId = row.id; leaderDlg.userId = 0; loadLeaders() }
async function assignLeader() {
  await api.post(`/org/groups/${leaderDlg.groupId}/leader`, { user_id: leaderDlg.userId })
  leaderDlg.show = false
  await loadAll()
}

function openCreateSubsys() { subsysDlg.show = true; subsysDlg.name = ''; subsysDlg.key = ''; subsysDlg.url = '' }
async function createSubsys() {
  await api.post('/subsystems', { name: subsysDlg.name, key: subsysDlg.key, url: subsysDlg.url })
  subsysDlg.show = false
  await loadAll()
}

async function setStatus(row: any, status: string) {
  await api.patch(`/subsystems/${row.id}`, { status })
  await loadAll()
}

function leaderName(_row: any) { return '' } // 简化：组列表暂不带组长名，实际可查 users
const statusLabel = (s: string) => ({ active: '运行中', stopped: '已停用', offline: '离线', archived: '已下线' }[s] || s)
const statusType = (s: string) => ({ active: 'success', stopped: 'warning', offline: 'info', archived: 'info' }[s] || 'default')

onMounted(loadAll)
</script>

<style scoped>
.admin { min-height: 100vh; background: var(--bg); }
.admin-header {
  display: flex; align-items: center; gap: 12px;
  height: 56px; padding: 0 20px;
  background: var(--surface); border-bottom: 1px solid var(--border);
}
.admin-title { font-weight: 600; color: var(--text); }
.admin-main { max-width: 1080px; margin: 0 auto; padding: 24px; display: grid; gap: 20px; }
.panel-head { display: flex; align-items: center; justify-content: space-between; }
.panel-title { font-weight: 600; color: var(--text); }
</style>
