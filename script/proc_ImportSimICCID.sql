CREATE DEFINER=`user_sim`@`%` PROCEDURE `proc_ImportSimICCID`(
    InStampId CHAR(36)
)
    SQL SECURITY INVOKER
    COMMENT '导入SimICCID'
BEGIN
# Author: wangcw
# Create: 2026-02-25 11:19:00
# Comment: 导入SimICCID

  /*
  1.先验证这些卡号是否都在siminfo表里面
  2.根据卡号验证在表tb_simiccid 是都有数据
  表tb_simiccid没有数据刷数逻辑
  1.更新表tb_simstatus 字段iccid（表格数据）、LastUpdateTime：当前时间
  2.表tb_simiccid 新增一条数据
  如果表tb_simiccid有数据
  1.更新表 tb_simstatus 字段iccid（表格数据）、LastUpdateTime：当前时间
  2.更新卡号，更新表 tb_simiccid 表里面的主键iccid的值
  */

  # 日志记录定义模块
  DECLARE sys_StartTime  DATETIME;
  DECLARE sys_ErrCode    VARCHAR(5) DEFAULT '00000';
  DECLARE sys_ErrMessage VARCHAR(1000);
  DECLARE Result INT DEFAULT 0;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN GET DIAGNOSTICS CONDITION 1
    sys_ErrCode=RETURNED_SQLSTATE,
	sys_ErrMessage=MESSAGE_TEXT;
	SET Result = -1;
	ROLLBACK;
    
    # 返回结果
    SELECT Result AS ErType,sys_ErrMessage AS ErMessage;
      
    # 日志记录生成模块
    INSERT INTO sys_procedurelog(IsSuccess,Logger,ProcedureName,TimeSpan,ErrCode,ErrMessage,LogTime)
    SELECT Result AS IsSuccess,
    'SimService' AS Logger,
    'proc_ImportSimICCID'   AS ProcedureName,
    TIMESTAMPDIFF(SECOND,sys_StartTime,NOW())   AS TimeSpan,
    sys_ErrCode    AS ErrCode,
    CONCAT('导入SimICCID失败，错误原因：',sys_ErrMessage) AS ErrMessage,
    NOW() AS LogTime;

  END;
  SET sys_StartTime=CURRENT_TIMESTAMP();

  # 更新空格等特殊字符
  UPDATE tm_simiccidimp
  SET SimNumber=REPLACE(SimNumber,' ',''),
  ICCID=REPLACE(ICCID,' ','')
  WHERE ImpStamp=InStampId;
  UPDATE tm_simiccidimp
  SET SimNumber=REPLACE(SimNumber,'	',''),
  ICCID=REPLACE(ICCID,'	','')
  WHERE ImpStamp=InStampId;
  UPDATE tm_simiccidimp
  SET SimNumber=REPLACE(SimNumber,'  ',''),
  ICCID=REPLACE(ICCID,'  ','')
  WHERE ImpStamp=InStampId;

  # 验证卡号是否都在siminfo表里面
  SELECT CONCAT(IFNULL(sys_ErrMessage,''), ErrMessage),-1 INTO sys_ErrMessage,Result
  FROM (SELECT CONCAT('有',r.TotalCount,'条SimNumber未录入SIM卡系统，请检查！') AS ErrMessage
  FROM (SELECT COUNT(*) AS TotalCount
  FROM tm_simiccidimp a
  WHERE NOT EXISTS (SELECT 1 
      FROM tb_siminfo b 
      WHERE a.SimNumber=b.SimNumber)
      AND a.ImpStamp=InStampId
  ) AS r
  WHERE r.TotalCount>0) AS s
  WHERE s.ErrMessage IS NOT NULL;

  IF Result=0 THEN
  # 开启事务
  START TRANSACTION;

  # 更新SIM卡是否存在ICCID状态
  UPDATE tm_simiccidimp a
  SET a.Existss=0
  WHERE NOT EXISTS (SELECT 1 
      FROM tb_simiccid b 
      WHERE a.SimNumber=b.SimNumber)
    AND a.Existss=1
    AND a.ImpStamp=InStampId;

  # ICCID 表没有数据
  UPDATE tb_simstatus a,
  tm_simiccidimp b
  SET a.ICCID=b.ICCID,
      a.LastUpdateTime=NOW()
  WHERE a.SimNumber=b.SimNumber
    AND b.Existss=0
    AND b.ImpStamp=InStampId;

  INSERT INTO tb_simiccid(ICCID,SimNumber,LastUpdateTime,SimId)
  SELECT b.ICCID,b.SimNumber,NOW(),a.Id
  FROM tb_siminfo a
  INNER JOIN tm_simiccidimp b
   ON a.SimNumber=b.SimNumber
   AND a.Deleted=0
  WHERE NOT EXISTS(SELECT 1 
    FROM tb_simiccid c 
    WHERE c.ICCID=b.ICCID)
    AND b.ImpStamp=InStampId;
 
  # ICCID 表有数据 
  UPDATE tb_simiccid a
  JOIN tm_simiccidimp b
    ON a.ICCID=b.ICCID
  SET a.SimNumber=b.SimNumber,
      a.LastUpdateTime=NOW()
  WHERE a.SimNumber=''
    AND b.ImpStamp=InStampId;

  # 事务提交/回滚模块
  IF (sys_ErrCode <> '00000' OR Result<>0)
  THEN
    SET Result=-1;
    ROLLBACK;
  ELSE
    COMMIT;
  END IF;

  END IF;

  # 返回结果
  SELECT Result AS ErType,sys_ErrMessage AS ErMessage;

  # 日志记录生成模块
  INSERT INTO sys_procedurelog(IsSuccess,Logger,ProcedureName,TimeSpan,ErrCode,ErrMessage,LogTime)
  SELECT Result AS IsSuccess,
  'SimService' AS Logger,
  'proc_ImportSimICCID'   AS ProcedureName,
  TIMESTAMPDIFF(SECOND,sys_StartTime,NOW())   AS TimeSpan,
  sys_ErrCode AS ErrCode,
  IFNULL(sys_ErrMessage,CONCAT('导入SimICCID完成!')) AS ErrMessage,
  NOW() AS LogTime;

END