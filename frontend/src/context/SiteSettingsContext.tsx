import React, { createContext, useContext, useState, useEffect } from 'react';

interface SiteSettings {
  siteTitle: string;
  siteLogo: string;
}

interface SiteSettingsContextType extends SiteSettings {
  refreshSettings: () => Promise<void>;
  loading: boolean;
}

const SiteSettingsContext = createContext<SiteSettingsContextType | undefined>(undefined);

export const SiteSettingsProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [siteTitle, setSiteTitle] = useState('YHCT Diamond');
  const [siteLogo, setSiteLogo] = useState('');
  const [loading, setLoading] = useState(true);

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  const fetchSettings = async () => {
    try {
      const res = await fetch(`${API_URL}/settings/public`);
      if (res.ok) {
        const data = await res.json();
        if (data.site_title) {
          setSiteTitle(data.site_title);
        }
        if (data.site_logo !== undefined) {
          setSiteLogo(data.site_logo);
        }
      }
    } catch (error) {
      console.error('Lỗi khi fetch public settings:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  return (
    <SiteSettingsContext.Provider value={{ siteTitle, siteLogo, refreshSettings: fetchSettings, loading }}>
      {children}
    </SiteSettingsContext.Provider>
  );
};

export const useSiteSettings = () => {
  const context = useContext(SiteSettingsContext);
  if (!context) {
    throw new Error('useSiteSettings must be used within a SiteSettingsProvider');
  }
  return context;
};
