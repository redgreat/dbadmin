<template>
  <AppPage :show-footer="false">
    <div flex-1>
      <n-card rounded-10>
        <div flex items-center justify-between>
          <div flex items-center>
            <div ml-10>
              <p text-20 font-semibold>数据运维中心</p>
              <p mt-5 text-14 op-60>欢迎使用数据运维中心，这里可以管理所有数据运维相关的功能</p>
            </div>
          </div>
        </div>
      </n-card>

      <n-card
        title="数据运维模块"
        size="small"
        :segmented="true"
        mt-15
        rounded-10
      >
        <div flex flex-wrap justify-between>
          <n-card
            v-for="item in moduleList"
            :key="item.id"
            class="mb-10 mt-10 w-300 cursor-pointer"
            hover:card-shadow
            :title="item.title"
            size="small"
            @click="navigateTo(item.path)"
          >
            <template #header-extra>
              <n-icon :component="renderIcon(item.icon)" />
            </template>
            <p op-60>{{ item.description }}</p>
          </n-card>
        </div>
      </n-card>
    </div>
  </AppPage>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { renderIcon } from '@/utils'

const router = useRouter()

// 模块列表
const moduleList = [
  {
    id: 1,
    title: '仓储中心',
    icon: 'mdi-printer-search',
    path: '/dm/wms',
    description: '管理仓储相关的数据和操作'
  },
  {
    id: 2,
    title: '订单中心',
    icon: 'mdi-cube-off',
    path: '/dm/oms',
    description: '管理订单相关的数据和操作'
  },
  {
    id: 3,
    title: '壹好车服',
    icon: 'mdi-motion-sensor-off',
    path: '/dm/ehcf',
    description: '管理壹好车服相关的数据和操作'
  }
]

// 导航到指定路径
const navigateTo = (path) => {
  router.push(path)
}
</script>
