import { createApp } from 'vue'
import Antd from 'ant-design-vue'
import App from './App.vue'

const app = createApp(App)
app.use(Antd)
app.mount('#app')
