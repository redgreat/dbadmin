from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "imptask" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "task_name" VARCHAR(100) NOT NULL,
    "filename" VARCHAR(255) NOT NULL,
    "file_path" VARCHAR(500) NOT NULL,
    "file_size" BIGINT NOT NULL,
    "db_type" VARCHAR(20) NOT NULL,
    "status" VARCHAR(20) NOT NULL DEFAULT 'pending',
    "progress" INT NOT NULL DEFAULT 0,
    "message" VARCHAR(500),
    "sql_file_path" VARCHAR(500),
    "sql_file_size" BIGINT,
    "error_message" TEXT,
    "started_at" TIMESTAMPTZ,
    "completed_at" TIMESTAMPTZ,
    "user_id" BIGINT,
    "username" VARCHAR(50)
);
CREATE INDEX IF NOT EXISTS "idx_imptask_created_435aab" ON "imptask" ("created_at");
CREATE INDEX IF NOT EXISTS "idx_imptask_updated_858cf7" ON "imptask" ("updated_at");
CREATE INDEX IF NOT EXISTS "idx_imptask_task_na_e0dfc1" ON "imptask" ("task_name");
CREATE INDEX IF NOT EXISTS "idx_imptask_status_991721" ON "imptask" ("status");
CREATE INDEX IF NOT EXISTS "idx_imptask_started_1e779a" ON "imptask" ("started_at");
CREATE INDEX IF NOT EXISTS "idx_imptask_complet_2c516e" ON "imptask" ("completed_at");
CREATE INDEX IF NOT EXISTS "idx_imptask_user_id_7fa251" ON "imptask" ("user_id");
CREATE INDEX IF NOT EXISTS "idx_imptask_status_98cb38" ON "imptask" ("status", "created_at");
CREATE INDEX IF NOT EXISTS "idx_imptask_user_id_e635df" ON "imptask" ("user_id", "status");
COMMENT ON COLUMN "imptask"."task_name" IS '任务名称';
COMMENT ON COLUMN "imptask"."filename" IS '原始文件名';
COMMENT ON COLUMN "imptask"."file_path" IS '文件存储路径';
COMMENT ON COLUMN "imptask"."file_size" IS '文件大小(字节)';
COMMENT ON COLUMN "imptask"."db_type" IS '数据库类型(mysql/postgresql)';
COMMENT ON COLUMN "imptask"."status" IS '任务状态(pending/processing/completed/failed)';
COMMENT ON COLUMN "imptask"."progress" IS '进度百分比(0-100)';
COMMENT ON COLUMN "imptask"."message" IS '进度消息';
COMMENT ON COLUMN "imptask"."sql_file_path" IS '生成的SQL文件路径';
COMMENT ON COLUMN "imptask"."sql_file_size" IS 'SQL文件大小(字节)';
COMMENT ON COLUMN "imptask"."error_message" IS '错误信息';
COMMENT ON COLUMN "imptask"."started_at" IS '开始处理时间';
COMMENT ON COLUMN "imptask"."completed_at" IS '完成时间';
COMMENT ON COLUMN "imptask"."user_id" IS '创建用户ID';
COMMENT ON COLUMN "imptask"."username" IS '创建用户名';
COMMENT ON TABLE "imptask" IS 'Excel导入任务模型';
        DROP TABLE IF EXISTS "excel_import_task";"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "imptask";"""


MODELS_STATE = (
    "eJztXW1zm0gS/isufXKqlAviXVt1H+zEu+tbO95LnL29TbZUAwwSZQRaXpL4tvzfb3oQYn"
    "g1IAmwzReXPExL8PQw0/10T8/fk7VrYNv/x9nGmvxw8vfEQWtMPrDN05MJ2mySRmgIkGbT"
    "fmjbQfMDD+kBaTKR7WPSZGBf96xNYLkOaXVC24ZGVycdLWeZNIWO9VeIF4G7xMEKe+TC5z"
    "9Js+UY+Dv24383dwvTwraRuknLgN+m7YvgfkPbzq3lpRP8SPvCD2oL3bXDtZP039wHK9fZ"
    "CVhOAK1L7GAPBRh+IfBCeAK4we1zxg8V3WzSJbpLRsbAJgrtgHnimjDorgMQkrvx6TMu4V"
    "dez3leEBSeE2RVEhVFUjmV9KW3lL+kPEQPnAASfRWF5fKny/e38KAu0VOkO2h4oDIoQJEU"
    "xTsBWPcwQLJAQR7od+RKYK1xMdRpyQzkxlb0H/GHrAJiuKs0EDccTwXkEYwbx77ffnUFur"
    "eX1xcfb8+uf4UHWfv+XzZF6Oz2Aq7wtPU+03oqv0qrY/clJ/+5vP35BP49+ePm/QUF0PWD"
    "pUd/Mel3+8cE7gmFgbtw3G8LZDAoxK0xUqRnotdwY7TUa1py1Gufet3efKLWDQpWeYW+XS"
    "GvWJlx/4waCVhdKm5y9uvll1Alvb6EkqmKk3paXKPvCxs7S/IIP5zMOK5Cjb+dfXj789mH"
    "U9Iro5v320t8dO0hBeeaLEhuwRIDgF444ZqCeknuCjk6zoGbSPcML8FWM5UvoayLPPkraX"
    "P4bEhtcJZroJwd/wnGchZhP1yvkXffZMwyIoPCVdFU7ksoYl1rg6tUa/xKFeNXyo/fAC39"
    "JtDG/YcwHcjEnAFQFdzrdACmp3nH2EbQoCH97hvyjEXuisu7ZX3zl9b8utDo8lwbL4hdXa"
    "C7a+Tc37rwNzf3ZJS2td8/kO9qo7xjm7cP8diLW5OfoHe+yPgh8XN42KbmR3x5B5PrUZTv"
    "8P0Owsja3ylge4lIbK8EK88NlysWcjoanAX5SRxEL8vZx7dn7+hSvch6CHRwrJGDlrQJHv"
    "RhmnhOoWEFV+5yUuRVxdemla4V9LK3vUb/avSvRv9qmHb46F89T73m/KvQx96iaFIsnREZ"
    "icenxSNbq4rEq8Sw4gXl8l1NoyqaJPmZqIiqIIu7uXHXUjUlxtNfGj/6uYFRysp0ZphOJt"
    "UAEkdV5AzSMje5Vm6UWMePEssdKTHnq7pGaDcCNpHoGVaJnxPPX+VMAqiM+BlpUSRlGLA+"
    "EQe1GNiU2y/oALLZbrzOeLWOP8Wr5f4UXKtPr5QM2e4plRrI7kWozOo5qhV+ahbWwZOAj0"
    "O6HxfIS1INTEmvUlDptcxEEKAgLPDIS1f+RKCzhf/1rHDV4jWZAMtxZGJVVG7Wz9JPbLAN"
    "+QXih1pF638pjDm5ztDkCtcqUSerlITnIrz4JgF2LpniKWkSJOlLKJqisfZfdQdxd/xUJd"
    "nx7vyt6zhY3wKVIzxS16dVpAfByKlFeExAAQoHK5uMqUoEWN8MDC1ISkwJNUfINhQdCZSR"
    "QBkd7ZFAGfW6N4HS1Pnv3PEvjfQxq8N+rv9RItXk2yg2DaBlRHpHN78aK7qiFS/etTyAOh"
    "Dz5QjzOYBX5DVogm7c/1jQJjbRY9iKWCBIyoqAAE+Bg79iq5HL1xq5fMXI5fMjd+N6BcCW"
    "Gkhx92N5AfVxVRD1UQUsjFxqSwQzdOpgZtMN8v1vrteImmJl+odW0nQ58vbBNeURFzXVdU"
    "yP/9qDQa8hv9mKxcj0D3F+zRrYGPbQuoCvusXfy6bWnUQrcLeL/UGwTVlbgs5HaNfDtspY"
    "vvj9NmUnxwieXp/9/iplK1/dvP8p7s4g/vbq5rwmMfhxjWx7SOxgIZ/FIp0QhaTza7AZeG"
    "IzyIaoATtrSNOTGWmVDJNn5aYn/K5v0tpoTRR4Rd4th/BP1Ur48frs6qqIX1wj767JeE8k"
    "eh/v0pyj3DdWhzPGB8IsXq43t8i/mxSQivGlaRWfaK03QdzpUUrx4ruObVgqTZ38ncnA6G"
    "JTo0vorJJRbCT5OKH4mZkgGKKK9PrMphRsO/058o8j/zjyVCP/OOp1Ws0/wlKwaOo1p4R6"
    "58rYZWWATKRpke9vCDAr079jJwmQjiTNdaDNJFWhkMvt3bujpCMAZIummR4pof6BToGrSS"
    "r5yyF13+yPo+ykocj51v8KhnWVOZUS65+yTAE+54F20znzlKJP/lF5lW+WutCJ8TX0KMc+"
    "lFES5jily+SbeLn7y27J1R068FFGb1TkP5ZRG0fMKNtgxwCUHlswE4rjdCvyZuO5OvZ9+K"
    "i76w1s/DHemIi8ucZAVEDuEIZEk+QzVqS7eaeMYQL4MQJCWlZg6PMcKEEzxFPudWxedB9A"
    "WRN80LJZynQi0jtnxOIqGypEUjjZHMyKSWawRSsjJSfYO9KKNDMhTjXjYASr4sd/X6XX0g"
    "EaLDsUmxstOdFWE8jhFJCD+ymaLtjzXG9ROuWUs9Q5wd5fh7k0m0NAAMa8aOJZk4mnh+CM"
    "147GSUsegMZ5XAW1KQDJ5LjYQ5XmnEimJZEuqbuE5P21MSBeJ0aqkrDb2W5tqNiM7MC0ra"
    "l6vPy8ZA2Xbr6sWsz23X95SD3yM2qwmWiPrZgdL1u9JBkdNLJaCHp7Mk+qZ6tVmGrdVhWp"
    "jK1eYyecFARWafu0Kqq6jnuMZSnGqOYY1RzCGjpGNV+KXp/RrgrB0OOtk/vFMg/PupYllP"
    "3r4837hgllnxzyxJ8NSw+mJ7blB392bASJpgHQStI85ktkTauZolcBKyBR7bFnnfPMyIcv"
    "yHrsYFlURHnqlF1kvqB3+5Md4fvtaala5WPcldLxrWSHt6VHO3Hrzhlx/0EhKskmjkoFtk"
    "H0SHnXA6++UAfXAdZidT0Dew0iYLv+/eZXy8KcB/9TrRuZOXCQa4M87ATNalalZPqFT+EF"
    "mR2afRWusvzFyjIMXDBlnruujZFTMmuychkoNSJ4rEhsSX4zGY8yD2+2yAONKM85Aq6k70"
    "/en9/cXKVMgfPLLDv/6fr8grz19J0nnayghHICMtZ1sNNou2VKqP9EDwXrYhStGsz8eYfx"
    "BtnW16JgYNUITsl1OIJ380OODYdEMdkQahpR3QxaDxuWh/VGY5aV6d2qms9oXRttDruExV"
    "ndIkHPrOgy+A5j1eX8c2SrLic41S67TN2y4rrLMZl8oMLLN5uSqsvRhWkVr+1u6tZbzqTz"
    "qaYB2SHYpHWhMPgmpqE0KEJU7wtG0nwkzUdydSTNR73uTZqTiX5ZxCiUG2yJRO9kjWhiIL"
    "4kYb4vrXgUZ0NfLdf+sgl3nkgcgDs/qC/HLszSTIWFWdPmwyTP3Q2FpdGoZmV6H9cyLa8p"
    "mpIO7rOG2ozow6RopHf/OMheEHPRMu9L6pdWLwSFX9DNetBgd4rC0YGuq+n55aXlnA0kOY"
    "f6XgVeTOyTlTsxXtxjTM4Z/YzRzxjCZDP6GS9FrwNLzmk5JYLdOzegzhOv8MPLzYGbbYJp"
    "3L93mp0Fdb8TOQ62a6wPsv1QPHucqPzUefb4ObI8eyYokSbbGUY9S7YzPPxeZHt+kTrQsZ"
    "TbY+Wfut62j1GotpKTKZPjJxsorcnJlCUbZ+B7DqG5Tz7uciE6muri5yjSXZHemI1E9RS3"
    "Q/2Aoa2ySniPl8GrXwMvjgJHbn/N8nd1hQ7sVz4jp3LPVKVyd3FoyeEN0paHXemqPEm5GN"
    "i9cpKPBmwSPfgSmuYM+SsMQtFNTk9WQbAZhs2ve80SluP+fcP9ltwHMfNVGSpbmRqm27db"
    "1ek4TqjGXZPlpmBuLS9JwIj0DS5s55Sh/oMqQoaoqED0AGOR7peGUhEzeqjkYItHf3O9u4"
    "VhNQrYsDLd4T95s3LX+A1YGI+pQZExHeVSqwMRj1IuzwudReg3C4yxMh3iTBCOf7Ua5d1u"
    "5mEEybDzdfEVeY1KzrMyvXMzioAgNVpVoZS/YKg0KdKEVZGD+guqoEdTd7RO/nLx33/+dn"
    "b16WLXQaN0DtWNiCGUJmK+ZgCz62kHectGeor7966j5DCACHYIgrO6GSbcwLq7YZNjbhiJ"
    "7sq3CTJXXMHNgKyHyLVLnXmpzA3+VaQILjZxlDkcNEReAAM2GEhQp4YX6qbBH7rCG5nxPE"
    "x+s4j5KMU+I9Uh/oVTvhLV+oGSV1GSNhzFANMN+NX1LZtDY1tWF7JyM0Fpacg+dhIU14WM"
    "ZneQodtkzHihhUFOvxuGuDqLmveebg66BWE8AONoM7iN/GABBmGb7J+ccCf1pZrQARzaTS"
    "iMhfnSEn9SUVvy1rRWeE54eArXRoVn6sc9qayaBjMrUwCrqX6fTVLGU0+2aUCHydEGIq1F"
    "scBno+5dIK1mXkNqU0CRTbuV+vGXDxAttAqJZSYUt91m1ulrPlPgDHtOEqMaxax522gyzw"
    "VQH46Z5BqjVRLTfHS/Hj2apcGWvVRkMrXy1dyy1/wLxpBn5yHPIZ5Z0C6ikfVL/VCHwwqm"
    "J9EBBdOTLVE0PSHmphOfgNB7rI4WT25lOqclh7a6soWXX7KxjB2jlXZZuYH5RAo2BGDbJP"
    "Nlq9YIvZ2FU3PlYUV6Piug2J9VzJis7ocrJRP0poj+L6fmEoneqTkWUNWk51zPzIHGtehh"
    "CY0CkLFA7zA/pVMVIDpyT1AMi4o0lU4TGamejyUaUixl5J4KMH4uZER+iaVOayPfjpHo/x"
    "TB/amGQ7w/OXonjW8e3B9dD1tL5xdcN9M9Tqp+WthW5MF76NuOZGCHVGFy+kM/u55pWn4B"
    "GxSn65dTQXHS1Ljredz13PsaOe6OfZ6BmFGvNXc993Jw0KGmxkn+rKAh7X5GtoUasds7gS"
    "N5ufWPwJoDydb27CWhDpJCOZJCPmd5jSy7CZI7gb7H55xDkImmaa0qtR4lx35DAGn0vu8E"
    "+h6WiiRIlAtoNSyPcOAz8v1vrldgUladI5DI9E5mSZoOpz2rXLs6wrxaZ58Tr5bvc4JruQ"
    "ruxCloXv86JXe0rNXcUC1LWmXrt8smpF0PrRQ2AcwPN9gr3m7zGNYp0e7gLk0YYPEWMaS2"
    "R9nwCkYKzL80eZgeviqJ0qDygWnWqe0urYJQTo181Z3ksA5D3abDixymp8lr0T6zlxey66"
    "Nqy6FKSDz36uiZehu1S6QzJSb2qiORjJBSmu0Me5a+mhQQbdsr0yqqDSV9BkO2PSOm7Wh5"
    "UV+x5xeG9svNSkak58yo+ige39XZ7oKu7X9H3Z8mgEeqOuAEhUf8VFSITkQGVSK66fJShO"
    "LBikF3ZxYULC8P/wdmyBA/"
)
