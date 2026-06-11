import { defineConfig } from 'wxt'
import path from 'path'

// See https://wxt.dev/api/config.html
export default defineConfig({
	modules: ['@wxt-dev/module-vue'],
  publicDir: 'public',
  dev: {
    server: {
      port: 5174,
    },
  },
	manifest: {
		default_locale: 'zh',
    name: '__MSG_extName__',
    description: '__MSG_extDescription__',
		version: '1.0.0',
		permissions: ['activeTab', 'scripting', 'storage', 'tabs', 'notifications'],
		host_permissions: ['<all_urls>', 'about:blank'],
		content_security_policy: {
			extension_pages: "script-src 'self' 'wasm-unsafe-eval' http://localhost:5174 http://localhost:3001; object-src 'self'"
		},
		action: {
			default_icon: {
				'16': 'icon/16.png',
				'32': 'icon/32.png',
				'48': 'icon/48.png',
				'128': 'icon/128.png',
			},
		},
		icons: {
			'16': 'icon/16.png',
			'32': 'icon/32.png',
			'48': 'icon/48.png',
			'128': 'icon/128.png',
		},
	},
  alias: {
    '@': path.resolve(__dirname, '.'),
  },
})
