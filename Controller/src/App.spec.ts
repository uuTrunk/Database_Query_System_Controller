import { mount } from '@vue/test-utils'
import { describe, it, expect, vi } from 'vitest'
import App from './App.vue'

// Mock global variables injected by Vite define
vi.stubGlobal('__AGENT_PORT__', '8000')
vi.stubGlobal('__TRAINING_PORT__', '8001')
vi.stubGlobal('__AUTH_USER__', 'admin')
vi.stubGlobal('__AUTH_PASS__', 'password123')

describe('App Component', () => {
    it('renders login page initially', () => {
        const wrapper = mount(App)
        expect(wrapper.text()).toContain('Data Copilot')
        expect(wrapper.find('input[type="text"]').exists()).toBe(true)
        expect(wrapper.find('input[type="password"]').exists()).toBe(true)
        expect(wrapper.find('button').text()).toContain('')
    })
    
    it('sets initial username and password from Vite config', () => {
        const wrapper = mount(App)
        const usernameInput = wrapper.find('input[type="text"]').element as HTMLInputElement
        const passwordInput = wrapper.find('input[type="password"]').element as HTMLInputElement
        expect(usernameInput.value).toBe('admin')
        expect(passwordInput.value).toBe('password123')
    })
})
