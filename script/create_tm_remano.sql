-- =============================================================
-- WMS_CONN 仓储中心正式库(whcenter) 部署脚本
-- 功能：创建 SIM卡重复入库验证 的临时导入表 tm_remano
-- 说明：页面导入的 Excel（仅一列 SimNumber）会先写入本表，
--       批次用 ImpStamp（每次导入生成的唯一 stamp）隔离。
-- 验证 SQL（InStamp = 本次导入的 ImpStamp 批次值）：
--         SELECT a.MaterialNo
--         FROM tb_materialinit a
--         JOIN tm_remano b
--           ON b.MaterialNo = a.MaterialNo
--           AND b.ImpStamp = InStamp
--         WHERE a.Deleted = 0;
--       命中即代表该 SimNumber 在系统中已存在 => 重复入库。
-- 执行库：whcenter（WMS_CONN 连接）
-- 注意：验证完成后可由服务删除本批次数据（DELETE ... WHERE ImpStamp=批次号）
-- =============================================================

CREATE TABLE IF NOT EXISTS tm_remano (
    MaterialNo VARCHAR(200) NOT NULL COMMENT '导入的物料编码（即SimNumber）',
    ImpStamp   CHAR(36)     NOT NULL COMMENT '批次号（每次导入生成的唯一stamp，对应验证SQL的InStamp）',
    CreatedAt  DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '写入时间',
    PRIMARY KEY (MaterialNo, ImpStamp),
    KEY IDX_TMREMANO_STAMP (ImpStamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COMMENT='SIM卡重复入库验证-临时导入表';
