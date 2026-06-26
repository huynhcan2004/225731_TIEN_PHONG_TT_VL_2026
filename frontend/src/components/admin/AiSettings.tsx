// frontend/src/components/admin/AiSettings.tsx
import React, { useState, useEffect } from 'react';
import { Save, Cpu, Key, AlertCircle, Loader2, Plus, Eye, EyeOff, Trash2, Coins, Edit2, Check, X } from 'lucide-react';
import { useLanguageTheme } from '../../context/LanguageThemeContext';

export const AiSettings = () => {
    const { t, language } = useLanguageTheme();
    const [config, setConfig] = useState({
        active_model: "gemini-2.5-flash",
        temperature: 0.7,
        system_prompt: "Bạn là chuyên gia Y học Cổ Truyền...",
        gemini_api_key: "",
        gemini_fallback_keys: [] as string[],
        openai_api_key: "",
        openai_fallback_keys: [] as string[],
        tokens_per_1000_vnd: 10000,
        cost_per_query: 1000.0,
        root_admin_email: "",
        qwen_api_url: "http://localhost:11434"
    });
    const [initialConfig, setInitialConfig] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [visibleKeys, setVisibleKeys] = useState<Record<string, boolean>>({});
    const [editingKeyId, setEditingKeyId] = useState<string | null>(null);
    const [editValue, setEditValue] = useState("");

    useEffect(() => {
        const fetchSettings = async () => {
            try {
                const token = localStorage.getItem('access_token');
                const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
                
                const res = await fetch(`${API_URL}/api/admin/settings`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                
                if (res.ok) {
                    const data = await res.json();
                    const formattedData = {
                        ...data,
                        gemini_fallback_keys: data.gemini_fallback_keys || [],
                        openai_fallback_keys: data.openai_fallback_keys || []
                    };
                    setConfig(formattedData);
                    setInitialConfig(JSON.parse(JSON.stringify(formattedData)));
                }
            } catch (error) {
                console.error("Lỗi lấy cấu hình:", error);
            } finally {
                setLoading(false);
            }
        };
        fetchSettings();
    }, []);

    const handleSave = async (configToSave: any = config, silent = false) => {
        setSaving(true);
        try {
            const token = localStorage.getItem('access_token');
            const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
            
            // Guard against React SyntheticEvent being passed when called directly via onClick={handleSave}
            const actualConfig = (configToSave && typeof configToSave === 'object' && 'active_model' in configToSave)
                ? configToSave
                : config;
            
            const res = await fetch(`${API_URL}/api/admin/settings/update`, {
                method: 'POST',
                headers: { 
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(actualConfig)
            });
            
            if (res.ok) {
                alert(silent 
                    ? (language === 'vi' ? "Đã cập nhật/xóa API Key thành công!" : "API Key updated/deleted successfully!") 
                    : (language === 'vi' ? "Lưu cấu hình thành công!" : "Configuration saved successfully!")
                );
                setInitialConfig(JSON.parse(JSON.stringify(actualConfig)));
                return true;
            } else {
                alert(language === 'vi' ? "Lỗi khi lưu cấu hình" : "Error saving configuration");
                return false;
            }
        } catch (error) {
            alert(language === 'vi' ? "Lỗi hệ thống" : "System error");
            return false;
        } finally {
            setSaving(false);
        }
    };

    const toggleKeyVisibility = (keyId: string) => {
        setVisibleKeys(prev => ({ ...prev, [keyId]: !prev[keyId] }));
    };

    // Tạo danh sách các key hiện tại
    const getKeysList = () => {
        const list = [];
        
        // 1. Gemini Primary (luôn hiện)
        list.push({
            id: 'gemini_primary',
            provider: 'Google Gemini',
            role: language === 'vi' ? 'Chính (Primary)' : 'Primary',
            value: config.gemini_api_key || "",
            isPrimary: true,
            placeholder: language === 'vi' ? "Nhập API Key Gemini chính..." : "Enter primary Gemini API Key...",
            onChange: (val: string) => setConfig(prev => ({ ...prev, gemini_api_key: val })),
            onDelete: async () => {
                if (window.confirm(language === 'vi' ? "Bạn có chắc chắn muốn xóa API Key Gemini chính?" : "Are you sure you want to delete the primary Gemini API Key?")) {
                    const newConfig = { ...config, gemini_api_key: "" };
                    setConfig(newConfig);
                    await handleSave(newConfig, true);
                }
            }
        });
        
        // 2. Gemini Fallbacks
        config.gemini_fallback_keys.forEach((key, index) => {
            list.push({
                id: `gemini_fallback_${index}`,
                provider: 'Google Gemini',
                role: language === 'vi' ? `Phụ (Fallback #${index + 1})` : `Fallback #${index + 1}`,
                value: key,
                isPrimary: false,
                placeholder: language === 'vi' ? `Nhập API Key Gemini phụ #${index + 1}...` : `Enter fallback Gemini API Key #${index + 1}...`,
                onChange: (val: string) => {
                    const newKeys = [...config.gemini_fallback_keys];
                    newKeys[index] = val;
                    setConfig(prev => ({ ...prev, gemini_fallback_keys: newKeys }));
                },
                onDelete: async () => {
                    if (window.confirm(language === 'vi' ? `Bạn có chắc chắn muốn xóa API Key Gemini phụ #${index + 1}?` : `Are you sure you want to delete fallback Gemini API Key #${index + 1}?`)) {
                        const newKeys = config.gemini_fallback_keys.filter((_, i) => i !== index);
                        const newConfig = { ...config, gemini_fallback_keys: newKeys };
                        setConfig(newConfig);
                        await handleSave(newConfig, true);
                    }
                }
            });
        });

        // 3. OpenAI Primary (luôn hiện)
        list.push({
            id: 'openai_primary',
            provider: 'OpenAI GPT',
            role: language === 'vi' ? 'Chính (Primary)' : 'Primary',
            value: config.openai_api_key || "",
            isPrimary: true,
            placeholder: "sk-...",
            onChange: (val: string) => setConfig(prev => ({ ...prev, openai_api_key: val })),
            onDelete: async () => {
                if (window.confirm(language === 'vi' ? "Bạn có chắc chắn muốn xóa API Key OpenAI chính?" : "Are you sure you want to delete the primary OpenAI API Key?")) {
                    const newConfig = { ...config, openai_api_key: "" };
                    setConfig(newConfig);
                    await handleSave(newConfig, true);
                }
            }
        });
        
        // 4. OpenAI Fallbacks
        config.openai_fallback_keys.forEach((key, index) => {
            list.push({
                id: `openai_fallback_${index}`,
                provider: 'OpenAI GPT',
                role: language === 'vi' ? `Phụ (Fallback #${index + 1})` : `Fallback #${index + 1}`,
                value: key,
                isPrimary: false,
                placeholder: language === 'vi' ? `Nhập API Key OpenAI phụ #${index + 1}...` : `Enter fallback OpenAI API Key #${index + 1}...`,
                onChange: (val: string) => {
                    const newKeys = [...config.openai_fallback_keys];
                    newKeys[index] = val;
                    setConfig(prev => ({ ...prev, openai_fallback_keys: newKeys }));
                },
                onDelete: async () => {
                    if (window.confirm(language === 'vi' ? `Bạn có chắc chắn muốn xóa API Key OpenAI phụ #${index + 1}?` : `Are you sure you want to delete fallback OpenAI API Key #${index + 1}?`)) {
                        const newKeys = config.openai_fallback_keys.filter((_, i) => i !== index);
                        const newConfig = { ...config, openai_fallback_keys: newKeys };
                        setConfig(newConfig);
                        await handleSave(newConfig, true);
                    }
                }
            });
        });

        return list;
    };

    const keysList = getKeysList();

    // Kiểm tra xem cấu hình hiện tại có khác cấu hình ban đầu hay không
    const hasUnsavedChanges = initialConfig ? (
        config.active_model !== initialConfig.active_model ||
        config.temperature !== initialConfig.temperature ||
        config.system_prompt !== initialConfig.system_prompt ||
        config.qwen_api_url !== initialConfig.qwen_api_url ||
        config.tokens_per_1000_vnd !== initialConfig.tokens_per_1000_vnd ||
        config.cost_per_query !== initialConfig.cost_per_query ||
        config.root_admin_email !== initialConfig.root_admin_email ||
        config.gemini_api_key !== initialConfig.gemini_api_key ||
        config.openai_api_key !== initialConfig.openai_api_key ||
        JSON.stringify(config.gemini_fallback_keys) !== JSON.stringify(initialConfig.gemini_fallback_keys) ||
        JSON.stringify(config.openai_fallback_keys) !== JSON.stringify(initialConfig.openai_fallback_keys)
    ) : false;

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center h-64 text-emerald-500">
                <Loader2 className="w-8 h-8 animate-spin mb-4" />
                <p className="font-bold text-sm text-emerald-400">{t('loadingConfig')}</p>
            </div>
        );
    }

    return (
        <div className="max-w-4xl bg-[#060e0a]/90 backdrop-blur-md rounded-3xl p-8 border border-emerald-500/10 shadow-2xl space-y-8 text-slate-100 relative">
            
            <div className="flex items-center justify-between border-b border-emerald-500/10 pb-4">
                <h2 className="text-xl font-black text-slate-100 flex items-center gap-2">
                    <Cpu className="w-6 h-6 text-emerald-400" /> {t('aiConfigTitle')}
                </h2>
                <div className="flex items-center gap-3">
                    {hasUnsavedChanges && (
                        <span className="text-[10px] font-black text-amber-400 bg-amber-950/40 px-3 py-1.5 rounded-lg border border-amber-500/30 animate-pulse uppercase tracking-wider">
                            {t('unsavedChanges')}
                        </span>
                    )}
                    <button 
                        onClick={() => handleSave()}
                        disabled={saving}
                        className={`font-black py-2 px-6 rounded-xl transition-all flex items-center gap-2 disabled:opacity-50 shadow-md uppercase tracking-wider text-xs border cursor-pointer ${
                            hasUnsavedChanges 
                                ? 'bg-amber-500 hover:bg-amber-600 text-white border-amber-400/30 ring-2 ring-amber-500/20' 
                                : 'bg-emerald-600 hover:bg-emerald-500 text-white border-emerald-400/20 shadow-emerald-950/20'
                        }`}
                    >
                        {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                        {t('saveConfig')}
                    </button>
                </div>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div className="space-y-5">
                    <h3 className="font-bold text-slate-200 flex items-center gap-2 mb-4">
                        <Cpu className="w-5 h-5 text-emerald-500/60" /> {t('aiParamsTitle')}
                    </h3>
                    <div>
                        <label className="text-xs font-bold text-emerald-400/80 uppercase ml-1">{t('activeModelLabel')}</label>
                        <select 
                            value={config.active_model}
                            onChange={(e) => setConfig({...config, active_model: e.target.value})}
                            className="w-full mt-1 p-3 bg-emerald-950/30 border border-emerald-500/20 rounded-xl text-sm font-semibold text-slate-100 outline-none focus:border-emerald-400 focus:bg-[#060e0a]"
                        >
                            <option value="gemini-2.5-flash" className="bg-[#060e0a]">{t('geminiOption')}</option>
                            <option value="gpt-4o-mini" className="bg-[#060e0a]">{t('gpt4oMiniOption')}</option>
                            <option value="gpt-4o" className="bg-[#060e0a]">{t('gpt4oOption')}</option>
                            <option value="qwen2.5-coder:7b" className="bg-[#060e0a]">Qwen 2.5 Coder 7B (Local)</option>
                        </select>
                    </div>

                    <div>
                        <label className="text-xs font-bold text-emerald-400/80 uppercase ml-1 flex justify-between">
                            {t('temperatureLabel')} <span className="text-emerald-300">{config.temperature}</span>
                        </label>
                        <input type="range" min="0" max="1" step="0.1" value={config.temperature} onChange={(e) => setConfig({...config, temperature: parseFloat(e.target.value)})} 
                            className="w-full h-2 bg-emerald-950 border-emerald-500/20 rounded-lg appearance-none cursor-pointer accent-emerald-500 mt-2" />
                    </div>

                    <div>
                        <label className="text-xs font-bold text-emerald-400/80 uppercase ml-1">{t('qwenUrlLabel')}</label>
                        <input 
                            type="text" 
                            value={config.qwen_api_url}
                            onChange={(e) => setConfig({...config, qwen_api_url: e.target.value})}
                            placeholder="http://localhost:11434"
                            className="w-full mt-1 p-3 bg-emerald-950/30 border border-emerald-500/20 rounded-xl text-sm font-mono text-slate-100 outline-none focus:border-emerald-400 focus:bg-emerald-950/50" 
                        />
                        <p className="text-[10px] text-slate-400 mt-1 ml-1">{t('qwenUrlHelp')}</p>
                    </div>

                    <div>
                        <h3 className="font-bold text-slate-200 flex items-center gap-2 mb-3 mt-4">
                            <Coins className="w-5 h-5 text-amber-400" /> {t('financeSettingsTitle')}
                        </h3>
                        
                        <div className="bg-emerald-950/40 p-5 rounded-2xl border border-emerald-500/15 space-y-5">
                            <div>
                                <span className="text-xs font-bold text-emerald-400/80 uppercase ml-1 block mb-1">{t('exchangeRateLabel')}</span>
                                <div className="relative">
                                    <input 
                                        type="number" 
                                        value={config.tokens_per_1000_vnd}
                                        onChange={(e) => setConfig({...config, tokens_per_1000_vnd: parseInt(e.target.value) || 0})}
                                        className="w-full p-3 pr-16 bg-emerald-950/20 border border-emerald-500/25 rounded-xl text-sm font-bold text-emerald-300 outline-none focus:border-emerald-400"
                                    />
                                    <div className="absolute right-4 top-1/2 -translate-y-1/2 text-xs text-emerald-400/60 font-bold">Tokens</div>
                                </div>
                                <p className="text-[10px] text-slate-400 mt-1 ml-1">{t('exchangeRateHelp')}</p>
                            </div>

                            <div>
                                <span className="text-xs font-bold text-emerald-400/80 uppercase ml-1 block mb-1">{t('costPerQueryLabel')}</span>
                                <div className="relative">
                                    <input 
                                        type="number" 
                                        value={config.cost_per_query}
                                        onChange={(e) => setConfig({...config, cost_per_query: parseFloat(e.target.value) || 0})}
                                        className="w-full p-3 pr-16 bg-emerald-950/20 border border-emerald-500/25 rounded-xl text-sm font-bold text-emerald-300 outline-none focus:border-emerald-400"
                                    />
                                    <div className="absolute right-4 top-1/2 -translate-y-1/2 text-xs text-emerald-400/60 font-bold">Tokens</div>
                                </div>
                                <p className="text-[10px] text-slate-400 mt-1 ml-1">
                                    {t('costPerQueryHelp')}{' '}
                                    <strong className="text-emerald-300">
                                        {config.tokens_per_1000_vnd > 0 
                                            ? Math.round((config.cost_per_query / config.tokens_per_1000_vnd) * 1000).toLocaleString(language === 'vi' ? 'vi-VN' : 'en-US') 
                                            : 0} {t('vndUnit')}
                                    </strong>{' '}
                                    {t('costPerQueryHelpSuffix')}
                                </p>
                            </div>

                            <div>
                                <span className="text-xs font-bold text-emerald-400/80 uppercase ml-1 block mb-1">{t('rootAdminEmailLabel')}</span>
                                <input 
                                    type="email" 
                                    value={config.root_admin_email}
                                    onChange={(e) => setConfig({...config, root_admin_email: e.target.value})}
                                    placeholder="huynhcan2004@gmail.com"
                                    className="w-full p-3 bg-[#060e0a]/40 border border-emerald-500/25 rounded-xl text-sm font-semibold text-emerald-300 outline-none focus:border-emerald-400"
                                />
                                <p className="text-[10px] text-slate-400 mt-1 ml-1">{t('rootAdminEmailHelp')}</p>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="flex flex-col h-full">
                    <h3 className="font-bold text-slate-200 flex items-center gap-2 mb-4">
                        <AlertCircle className="w-5 h-5 text-emerald-500/60" /> {t('systemPromptLabel')}
                    </h3>
                    <div className="flex-1 flex flex-col">
                        <label className="text-xs font-bold text-emerald-400/80 uppercase ml-1 block mb-2">{t('systemPromptLabel')}</label>
                        <textarea className="w-full flex-1 min-h-[300px] p-4 bg-emerald-950/30 border border-emerald-500/20 rounded-xl text-sm font-medium text-slate-100 outline-none focus:border-emerald-400 focus:bg-[#060e0a] resize-y leading-relaxed" 
                            value={config.system_prompt} onChange={(e) => setConfig({...config, system_prompt: e.target.value})} />
                    </div>
                </div>
            </div>

            <div className="border-t border-emerald-500/10 pt-8 space-y-6">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                        <h3 className="text-lg font-black text-slate-100 flex items-center gap-2">
                            <Key className="w-5 h-5 text-amber-400" /> {t('apiKeyManagerTitle')} ({keysList.length})
                        </h3>
                        <p className="text-xs text-slate-400 mt-1">{t('apiKeyManagerHelp')}</p>
                    </div>
                    
                    <div className="flex gap-2">
                        <button 
                            onClick={() => setConfig({...config, gemini_fallback_keys: [...config.gemini_fallback_keys, ""]})}
                            className="text-xs font-bold text-emerald-400 flex items-center gap-1 hover:text-emerald-300 py-2 px-3.5 bg-emerald-950/45 hover:bg-emerald-950/70 border border-emerald-500/20 rounded-xl transition-all shadow-sm cursor-pointer"
                        >
                            <Plus className="w-4 h-4" /> {t('addGeminiFallback')}
                        </button>
                        <button 
                            onClick={() => setConfig({...config, openai_fallback_keys: [...config.openai_fallback_keys, ""]})}
                            className="text-xs font-bold text-purple-400 flex items-center gap-1 hover:text-purple-300 py-2 px-3.5 bg-purple-950/45 hover:bg-purple-950/70 border border-purple-500/20 rounded-xl transition-all shadow-sm cursor-pointer"
                        >
                            <Plus className="w-4 h-4" /> {t('addOpenaiFallback')}
                        </button>
                    </div>
                </div>

                {hasUnsavedChanges && (
                    <div className="bg-amber-950/30 border border-amber-500/30 p-4 rounded-2xl flex items-center gap-3 text-amber-300 text-xs font-bold animate-fadeIn">
                        <AlertCircle className="w-5 h-5 text-amber-400 flex-shrink-0" />
                        <div>
                            <span>{t('unsavedWarning')}</span>
                        </div>
                    </div>
                )}

                <div className="bg-[#050c08]/90 rounded-2xl border border-emerald-500/10 overflow-hidden shadow-inner">
                    <table className="w-full text-left border-collapse text-sm">
                        <thead>
                            <tr className="bg-emerald-950/40 border-b border-emerald-500/10 text-emerald-400 font-bold text-xs uppercase tracking-wider">
                                <th className="p-4 w-[180px]">{t('providerCol')}</th>
                                <th className="p-4 w-[160px]">{t('roleCol')}</th>
                                <th className="p-4">{t('keyCol')}</th>
                                <th className="p-4 text-center w-[120px]">{t('actionsCol')}</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-emerald-500/5 bg-[#060e0a]/50">
                            {keysList.length === 0 ? (
                                <tr>
                                    <td colSpan={4} className="p-8 text-center text-slate-500 italic">
                                        {t('noApiKeys')}
                                    </td>
                                </tr>
                            ) : (
                                keysList.map((k) => (
                                    <tr key={k.id} className="hover:bg-emerald-950/20 transition-colors">
                                        <td className="p-4 font-bold text-slate-300">
                                            <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold ${k.provider === 'Google Gemini' ? 'bg-blue-950/40 text-blue-400 border border-blue-500/20' : 'bg-purple-950/40 text-purple-400 border border-purple-500/20'}`}>
                                                {k.provider}
                                            </span>
                                        </td>
                                        <td className="p-4 font-bold text-slate-300">
                                            <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold ${k.isPrimary ? 'bg-emerald-950/50 text-emerald-400 border border-emerald-500/20' : 'bg-amber-950/40 text-amber-400 border border-amber-500/20'}`}>
                                                {k.role}
                                            </span>
                                        </td>
                                        <td className="p-4">
                                            <div className="relative flex items-center">
                                                <input 
                                                    type={visibleKeys[k.id] ? "text" : "password"} 
                                                    value={editingKeyId === k.id ? editValue : k.value}
                                                    onChange={(e) => setEditValue(e.target.value)}
                                                    readOnly={editingKeyId !== k.id}
                                                    placeholder={k.placeholder}
                                                    className={`w-full p-2.5 pr-10 border rounded-xl font-mono text-xs text-slate-200 transition-all outline-none ${
                                                        editingKeyId === k.id
                                                            ? "bg-[#060e0a] border-emerald-400/60 focus:border-emerald-400"
                                                            : "bg-emerald-950/10 border-emerald-500/10 focus:border-transparent opacity-80 cursor-default"
                                                    }`}
                                                />
                                                <button
                                                    onClick={() => toggleKeyVisibility(k.id)}
                                                    className="absolute right-3 p-1 text-slate-400 hover:text-slate-200 transition-colors cursor-pointer"
                                                    title={visibleKeys[k.id] ? t('hideKey') : t('showKey')}
                                                >
                                                    {visibleKeys[k.id] ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                                                </button>
                                            </div>
                                        </td>
                                        <td className="p-4 text-center">
                                            <div className="flex items-center justify-center gap-1.5">
                                                {editingKeyId === k.id ? (
                                                    <>
                                                        <button 
                                                            onClick={async () => {
                                                                k.onChange(editValue);
                                                                setEditingKeyId(null);
                                                                setEditValue("");
                                                                
                                                                let newConfig = { ...config };
                                                                if (k.id === 'gemini_primary') {
                                                                    newConfig.gemini_api_key = editValue;
                                                                } else if (k.id === 'openai_primary') {
                                                                    newConfig.openai_api_key = editValue;
                                                                } else if (k.id.startsWith('gemini_fallback_')) {
                                                                    const idx = parseInt(k.id.split('_')[2]);
                                                                    const newKeys = [...config.gemini_fallback_keys];
                                                                    newKeys[idx] = editValue;
                                                                    newConfig.gemini_fallback_keys = newKeys;
                                                                } else if (k.id.startsWith('openai_fallback_')) {
                                                                    const idx = parseInt(k.id.split('_')[2]);
                                                                    const newKeys = [...config.openai_fallback_keys];
                                                                    newKeys[idx] = editValue;
                                                                    newConfig.openai_fallback_keys = newKeys;
                                                                }
                                                                await handleSave(newConfig, true);
                                                            }}
                                                            className="p-2 text-emerald-400 hover:bg-emerald-950/40 border border-emerald-500/25 rounded-lg transition-colors cursor-pointer"
                                                            title={t('confirmEdit')}
                                                        >
                                                            <Check className="w-3.5 h-3.5" />
                                                        </button>
                                                        <button 
                                                            onClick={() => {
                                                                setEditingKeyId(null);
                                                                setEditValue("");
                                                            }}
                                                            className="p-2 text-rose-400 hover:bg-rose-950/40 border border-rose-500/25 rounded-lg transition-colors cursor-pointer"
                                                            title={t('cancel')}
                                                        >
                                                            <X className="w-3.5 h-3.5" />
                                                        </button>
                                                    </>
                                                ) : (
                                                    <>
                                                        <button 
                                                            onClick={() => {
                                                                setEditingKeyId(k.id);
                                                                setEditValue(k.value);
                                                            }}
                                                            className="p-2 text-amber-400 hover:bg-amber-950/30 border border-amber-500/20 rounded-lg transition-colors cursor-pointer"
                                                            title={t('editKey')}
                                                        >
                                                            <Edit2 className="w-3.5 h-3.5" />
                                                        </button>
                                                        <button 
                                                            onClick={k.onDelete}
                                                            className="p-2 text-rose-400/80 hover:bg-rose-950/30 border border-rose-500/20 rounded-lg transition-colors cursor-pointer"
                                                            title={t('deleteKey')}
                                                        >
                                                            <Trash2 className="w-3.5 h-3.5" />
                                                        </button>
                                                    </>
                                                )}
                                            </div>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>

                <div className="flex justify-end gap-3 pt-2">
                    {hasUnsavedChanges && (
                        <button 
                            onClick={() => handleSave()}
                            disabled={saving}
                            className="bg-amber-500 hover:bg-amber-600 border border-amber-400/20 text-white font-bold py-2.5 px-6 rounded-xl transition-all flex items-center gap-2 shadow-sm ring-2 ring-amber-500/20 animate-pulse cursor-pointer uppercase tracking-wider text-xs"
                        >
                            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                            {t('confirmSaveAll')}
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
};