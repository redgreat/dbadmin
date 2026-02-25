import i18n from '~/i18n'
const { t } = i18n.global

export default {
  name: t('views.tool.label_tool'),
  path: '/tools',
  component: 'Layout',
  meta: {
    title: t('views.tool.label_tool'),
    icon: 'mdi:tools',
    order: 4,
  },
  children: [
    {
      name: t('views.tool.label_excelimp'),
      path: 'excelimp',
      component: '/tool/excelimp',
      meta: {
        title: t('views.tool.label_excelimp'),
        icon: 'mdi:file-excel-outline',
      },
    },
    {
      name: t('views.tool.label_formatter'),
      path: 'formatter',
      component: '/tool/formatter',
      meta: {
        title: t('views.tool.label_formatter'),
        icon: 'mdi:code-braces',
      },
    },
  ],
}
