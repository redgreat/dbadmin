DROP PROCEDURE IF EXISTS `proc_VhsAcceptRefesh`;
CREATE DEFINER=`user_service`@`%` PROCEDURE `proc_VhsAcceptRefesh`(
InStampId CHAR(36) # 临时表Id
)
    SQL SECURITY INVOKER
    COMMENT '车务待办人刷新'
BEGIN
# Author: wangcw
# Create: 2026-9-22 10:43:05
# Comment: 车务待办人刷新

  # 日志记录定义模块
  DECLARE sys_StartTime  DATETIME;
  DECLARE sys_ErrCode    VARCHAR(5) DEFAULT '00000';
  DECLARE sys_ErrMessage VARCHAR(200);
  DECLARE Result SMALLINT DEFAULT 0;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
  GET DIAGNOSTICS CONDITION 1
    sys_ErrCode = RETURNED_SQLSTATE,
    sys_ErrMessage = MESSAGE_TEXT;
  SET Result = -1;
  ROLLBACK;

  SELECT Result AS ErType,sys_ErrMessage AS ErMessage;

  INSERT INTO sys_procedurelog(IsSuccess,Logger,ProcedureName,TimeSpan,ErrCode,ErrMessage,LogTime)
  SELECT Result AS IsSuccess,
  'AcceptRefeshService' AS Logger,
  'proc_VhsAcceptRefesh'   AS ProcedureName,
  TIMESTAMPDIFF(SECOND,sys_StartTime,NOW())   AS TimeSpan,
  sys_ErrCode AS ErrCode,
  IFNULL(sys_ErrMessage,'') AS ErrMessage,
  NOW() AS LogTime;

  END;
  SET sys_StartTime=CURRENT_TIMESTAMP();

  # 开启事务
  START TRANSACTION;

  -- 1. 刷新工作流待办人（workflowruntimeactors）
  UPDATE tm_newaccept a
  JOIN tb_workorderinfo b
    ON b.AppCode=a.AppCode
    AND b.WorkStatus=6
    AND b.Deleted=0
  JOIN workflowruntimeitems c
    ON c.TargetEntityId = b.Id
    AND c.Deleted=0
  JOIN workflowruntimesteps d
    ON d.RuntimeItemId=c.Id
    AND d.Status IN ('PROCESSING','SUSPENDED')
    AND d.Name='提交处理结果'
    AND d.Deleted=0
  JOIN workflowruntimeactors e
    ON e.RuntimeStepId = d.Id
    AND e.Status='PROCESSING'
    AND e.Deleted=0
  SET e.LoginName=a.NAcceptCode,
  e.FullName=a.NAcceptName,
  e.UserId=a.NAcceptId
  WHERE a.ImpStamp=InStampId;

  -- 2. 刷新工单操作记录（tb_operatinginfo）
  UPDATE tm_newaccept a
  JOIN tb_workorderinfo b
    ON b.AppCode=a.AppCode
    AND b.WorkStatus=6
    AND b.Deleted=0
  JOIN tb_operatinginfo c
    ON c.WorkOrderId=b.Id
    AND c.Deleted=0
  SET c.OperId=a.NAcceptId,
  c.OperCode=a.NAcceptCode,
  c.OperName=a.NAcceptName
  WHERE a.ImpStamp=InStampId;

  -- 3. 刷新工作流状态（workflowruntimestatus）：按工单 TargetEntityId 定位状态行
  UPDATE workflowruntimestatus s
  JOIN tm_newaccept a
    ON a.AppCode=(SELECT b.AppCode
        FROM tb_workorderinfo b
        WHERE b.Id=s.TargetEntityId
        AND b.Deleted=0)
  SET s.WorkflowStatus='PROCESSING', s.WorkflowStatusText='处理中',
      s.PreStepName='分派工单', s.PreStepNodeCode='Multiple001_Distribute',
      s.PreStepHandlingStatusName='我来接单', s.PreStepHandlingStatusCode='RECEIVE',
      s.CurrentStepName='提交处理结果', s.CurrentStepNodeCode='Multiple001_Record',
      s.CurrentStepStatus='PROCESSING'
  WHERE s.Deleted=0
    AND a.ImpStamp=InStampId;

  # 事务提交/回滚模块
  IF sys_ErrCode<>'00000'
  THEN
  	SET Result=-1;
  	ROLLBACK;
  ELSE
  	SET Result=0;
  	COMMIT;
  END IF;

  # 删除已处理的记录
  DELETE FROM tm_newaccept
  WHERE ImpStamp=InStampId;

  # 返回成功值
  SELECT Result AS ErType,sys_ErrMessage AS ErMessage;

  # 日志记录生成模块
  INSERT INTO sys_procedurelog(IsSuccess,Logger,ProcedureName,TimeSpan,ErrCode,ErrMessage,LogTime)
  SELECT Result AS IsSuccess,
  'AcceptRefeshService' AS Logger,
  'proc_VhsAcceptRefesh'   AS ProcedureName,
  TIMESTAMPDIFF(SECOND,sys_StartTime,NOW())   AS TimeSpan,
  sys_ErrCode AS ErrCode,
  IFNULL(sys_ErrMessage,'') AS ErrMessage,
  NOW() AS LogTime;

END
