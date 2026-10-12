"""Atualização mensal isolada; publica somente após validação de todas as camadas."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import argparse,json,os,shutil,subprocess,sys,tomllib,uuid
from configuracao import RAIZ,ESTADO,DADOS

def intervalo(hoje,cfg,inicio=None,fim=None):
    fim=hoje.year if fim is None else fim
    inicio=max(cfg['ano_inicial_historico'],hoje.year-cfg['anos_reprocessamento']+1) if inicio is None else inicio
    if not cfg['ano_inicial_historico']<=inicio<=fim<=hoje.year:raise ValueError('Intervalo de atualização inválido.')
    return inicio,fim

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--inicio',type=int);ap.add_argument('--fim',type=int)
    ap.add_argument('--forcar',action='store_true')
    ap.add_argument('--planejar',action='store_true',help='Exibe o plano sem acessar a rede.')
    ap.add_argument('--publicar-local',action='store_true',help='Copia dados validados para o checkout; executar com app local parado.')
    args=ap.parse_args()
    cfg=tomllib.loads((RAIZ/'config.toml').read_text())['atualizacao']
    hoje=datetime.now(ZoneInfo('America/Sao_Paulo')).date()
    inicio,fim=intervalo(hoje,cfg,args.inicio,args.fim)
    anos=[a for a in range(inicio,fim+1) if a<hoje.year or hoje.month>1]
    plano={'inicio':inicio,'fim':fim,'anos_complementos':anos,'motor':cfg['motor'],'estado':str(ESTADO),'publicar_local':args.publicar_local}
    if args.planejar:print(json.dumps(plano,ensure_ascii=False,indent=2));return
    if not anos:raise ValueError('Nenhum ano com meses encerrados no intervalo.')
    ESTADO.mkdir(parents=True,exist_ok=True)
    lock=ESTADO/'atualizacao.lock'
    fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    os.write(fd,str(os.getpid()).encode());os.close(fd)
    lote=ESTADO/'lotes'/(datetime.now().strftime('%Y%m%dT%H%M%S')+'_'+uuid.uuid4().hex[:8])
    destino=lote/'dados'
    env=os.environ.copy();env.update(TCC_DADOS_DIR=str(destino),TCC_ETL_RAIZ=str(ESTADO),TCC_TABNET_MOTOR=cfg['motor'],TCC_INTERVALO_SEGUNDOS=str(cfg['intervalo_segundos']))
    report={'plano':plano,'status':'executando','lote':str(lote)}
    def run(*cmd):subprocess.run([sys.executable,*cmd],cwd=RAIZ,env=env,check=True)
    try:
        lote.mkdir(parents=True)
        shutil.copytree(DADOS,destino)
        force=['--forcar'] if args.forcar else []
        run('-m','etl.executar_base','--inicio',str(inicio),'--fim',str(fim),*force)
        run('-m','etl.incorporar_lote',str(ESTADO))
        for module in ['extrair_raca_cor','extrair_meios_cid']:
            run('-m','etl.'+module,'--inicio',str(min(anos)),'--fim',str(max(anos)),*force)
        run('-m','etl.validar','--anos',*[str(a) for a in anos])
        report['status']='validado'
        if args.publicar_local:
            backup=lote/'dados_anteriores';shutil.copytree(DADOS,backup)
            try:
                for file in destino.iterdir():
                    if file.is_file():
                        temp=DADOS/(file.name+'.tmp');shutil.copy2(file,temp);os.replace(temp,DADOS/file.name)
            except BaseException:
                for file in backup.iterdir():shutil.copy2(file,DADOS/file.name)
                raise
            report['status']='publicado_no_checkout'
    except BaseException as exc:
        report['status']='falhou';report['erro']=str(exc);raise
    finally:
        try:
            if lote.exists():
                (lote/'execucao.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
        finally:
            lock.unlink(missing_ok=True)
            print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
