import i18n from '~/i18n'
const { t } = i18n.global

export default {
  name: t('views.conn.label_conn'),
  path: '/conn',
  component: 'Layout',
  meta: {
    title: t('views.conn.label_conn'),
    icon: 'material-symbols:database',
    order: 3,
  },
  children: [
    {
      name: t('views.conn.label_conn_manage'),
      path: '',
      component: '/conn',
      meta: {
        title: t('views.conn.label_conn_manage'),
        icon: 'material-symbols:database-outline',
      },
    },
  ],
}
