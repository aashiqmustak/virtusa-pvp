import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
export default defineConfig({plugins:[vue()],server:{allowedHosts:['terminal.local'],proxy:{'/api':{target:'http://localhost:8000',ws:true},'/schema':'http://localhost:8000'}},build:{outDir:'dist'}})
