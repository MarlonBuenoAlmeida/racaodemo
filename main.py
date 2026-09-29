import os
import sys
from tkinter import messagebox, ttk
import customtkinter as ctk
import fdb

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CAMINHOS_DLL_32 = [
    os.path.join(BASE_DIR, "fbclient.dll"),
    r"C:\SUAPASTA\fbclient.dll",
]

dll_carregada = False

for path in CAMINHOS_DLL_32:
    if os.path.exists(path):
        try:
            fdb.load_api(path)
            dll_carregada = True
            print(f"DLL 32-bits carregada com sucesso: {path}")
            break
        except Exception as err:
            print(f"Tentou carregar {path}, mas falhou: {err}")

if not dll_carregada:
    try:
        fdb.load_api("fbclient.dll")
        print("DLL carregada a partir das variáveis de ambiente (PATH).")
    except Exception as err:
        print(f"Aviso crítico ao carregar DLL do Firebird: {err}")

DB_CONFIG = {
    'host': 'localhost',
    'database': r'C:\SEUCAMINHO\SEUBANCO.FDB',
    'user': 'ADMIN',
    'password': '1234',
    'charset': 'WIN1252'
}

def get_connection():
    return fdb.connect(**DB_CONFIG)

def inicializar_estrutura_banco():
    """Garante a existência das colunas e tabelas necessárias no banco."""
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            
            try:
                cur.execute("""
                    CREATE TABLE NOTIFICACAO_PRECO (
                        ID INTEGER NOT NULL PRIMARY KEY,
                        PRODUTO_ID INTEGER NOT NULL,
                        CUSTO_ANT DOUBLE PRECISION,
                        VMIN_ANT DOUBLE PRECISION,
                        VMAX_ANT DOUBLE PRECISION,
                        CUSTO_ATU DOUBLE PRECISION,
                        VMIN_ATU DOUBLE PRECISION,
                        VMAX_ATU DOUBLE PRECISION
                    )
                """)
                conn.commit()
            except Exception:
                pass

            try:
                cur.execute("""
                    CREATE TABLE REAJUSTE_TEMPORARIO (
                        PRODUTO_ID INTEGER NOT NULL PRIMARY KEY,
                        VMAX_ORIGINAL DOUBLE PRECISION,
                        FRETE_UNIT DOUBLE PRECISION,
                        COMISSAO_UNIT DOUBLE PRECISION,
                        VMAX_TEMPORARIO DOUBLE PRECISION,
                        ESTOQUE_BASE DOUBLE PRECISION,
                        QTD_APLICADA DOUBLE PRECISION
                    )
                """)
                conn.commit()
            except Exception:
                pass

            try:
                cur.execute("""
                    CREATE TABLE INGREDIENTE (
                        ID INTEGER NOT NULL PRIMARY KEY,
                        DESCRICAO VARCHAR(100),
                        PRECO_CUSTO DOUBLE PRECISION,
                        ESTOQUE DOUBLE PRECISION DEFAULT 0,
                        ESTOQUEMIN DOUBLE PRECISION DEFAULT 0
                    )
                """)
                conn.commit()
            except Exception:
                pass

            try:
                cur.execute("ALTER TABLE REAJUSTE_TEMPORARIO ADD QTD_APLICADA DOUBLE PRECISION DEFAULT 0")
                conn.commit()
            except Exception:
                pass

            try:
                cur.execute("ALTER TABLE INGREDIENTE ADD ESTOQUE DOUBLE PRECISION DEFAULT 0")
                conn.commit()
            except Exception:
                pass

            try:
                cur.execute("ALTER TABLE INGREDIENTE ADD ESTOQUEMIN DOUBLE PRECISION DEFAULT 0")
                conn.commit()
            except Exception:
                pass

    except Exception as e:
        print(f"Aviso ao verificar estrutura do banco: {e}")


class JanelaSenha(ctk.CTkToplevel):
    def __init__(self, parent, senha_correta="1989"):
        super().__init__(parent)
        self.senha_correta = senha_correta
        self.autenticado = False

        self.title("Acesso Restrito")
        self.geometry("350x200")
        self.resizable(False, False)

        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.ao_fechar)

        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

        lbl_titulo = ctk.CTkLabel(self, text="🔒 Digite a Senha de Acesso", font=("Arial", 15, "bold"))
        lbl_titulo.pack(pady=(20, 10))

        self.entry_senha = ctk.CTkEntry(self, show="*", width=200, placeholder_text="Senha...")
        self.entry_senha.pack(pady=10)
        self.entry_senha.focus()
        self.entry_senha.bind("<Return>", lambda e: self.verificar_senha())

        btn_entrar = ctk.CTkButton(
            self, text="Entrar", command=self.verificar_senha, 
            fg_color="green", font=("Arial", 12, "bold"), width=120
        )
        btn_entrar.pack(pady=10)

    def verificar_senha(self):
        senha_digitada = self.entry_senha.get().strip()
        if senha_digitada == self.senha_correta:
            self.autenticado = True
            self.grab_release()
            self.destroy()
        else:
            messagebox.showerror("Erro de Acesso", "Senha incorreta! Tente novamente.", parent=self)
            self.entry_senha.delete(0, 'end')

    def ao_fechar(self):
        self.autenticado = False
        self.grab_release()
        self.destroy()


class JanelaEdicaoFichaTecnica(ctk.CTkToplevel):
    def __init__(self, parent, produto_id, produto_nome, on_close_callback=None):
        super().__init__(parent)
        self.produto_id = produto_id
        self.produto_nome = produto_nome
        self.on_close_callback = on_close_callback
        self.ingredientes_edit = []

        self.title(f"Ficha Técnica - ID {produto_id}: {produto_nome}")
        self.geometry("750x550")
        self.grab_set()

        lbl_titulo = ctk.CTkLabel(
            self, text=f"Ficha Técnica / Receita\n{produto_nome} (ID: {produto_id})",
            font=("Arial", 16, "bold")
        )
        lbl_titulo.pack(pady=10)

        self.scroll_ingredientes = ctk.CTkScrollableFrame(self, height=350)
        self.scroll_ingredientes.pack(fill="both", expand=True, padx=20, pady=5)

        self.btn_add_ing = ctk.CTkButton(
            self, text="+ Adicionar Ingrediente à Receita",
            command=self.adicionar_linha_ingrediente, height=30
        )
        self.btn_add_ing.pack(padx=20, pady=5, anchor="w")

        self.lbl_custo_total = ctk.CTkLabel(
            self, text="Custo Calculado: R$ 0.00", font=("Arial", 13, "bold"), text_color="cyan"
        )
        self.lbl_custo_total.pack(pady=5)

        frame_botoes = ctk.CTkFrame(self)
        frame_botoes.pack(fill="x", padx=20, pady=10)

        btn_salvar = ctk.CTkButton(
            frame_botoes, text="Salvar Receita", command=self.salvar_receita,
            fg_color="green", font=("Arial", 13, "bold"), height=35
        )
        btn_salvar.pack(side="right", padx=10)

        btn_cancelar = ctk.CTkButton(
            frame_botoes, text="Cancelar", command=self.destroy,
            fg_color="gray", font=("Arial", 13, "bold"), height=35
        )
        btn_cancelar.pack(side="right", padx=10)

        self.carregar_ingredientes_existentes()

    def carregar_ingredientes_existentes(self):
        try:
            with get_connection() as conn:
                cur = conn.cursor()
                query = """
                    SELECT ft.INGREDIENTE_ID, i.DESCRICAO, ft.QUANTIDADE, ft.UNIDADE, i.PRECO_CUSTO
                    FROM PRODUTO_COMPOSTO pc
                    JOIN FICHA_TECNICA ft ON ft.COMPOSTO_ID = pc.ID
                    JOIN INGREDIENTE i ON i.ID = ft.INGREDIENTE_ID
                    WHERE pc.PRODUTO_ID = ?
                """
                cur.execute(query, (int(self.produto_id),))
                rows = cur.fetchall()

            for ing_id, desc, qtd, un, pcusto in rows:
                pcusto = float(pcusto) if pcusto is not None else 0.0
                qtd = float(qtd) if qtd is not None else 0.0
                self.adicionar_linha_ingrediente(
                    ing_id=ing_id, desc=desc, qtd=qtd, un=un or "kg", pcompra=pcusto
                )

            self.recalcular_custo_total()

        except Exception as e:
            messagebox.showerror("Erro de Banco", f"Erro ao carregar ingredientes:\n{e}", parent=self)

    def adicionar_linha_ingrediente(self, ing_id=None, desc="", qtd=0.0, un="kg", pcompra=0.0):
        row_frame = ctk.CTkFrame(self.scroll_ingredientes)
        row_frame.pack(fill="x", pady=4, padx=5)

        txt_busca = ctk.CTkEntry(row_frame, width=110, placeholder_text="ID / Nome...")
        txt_busca.pack(side="left", padx=3)

        cmb_ing = ctk.CTkOptionMenu(row_frame, values=["Selecione ou busque ao lado"], width=210)
        cmb_ing.pack(side="left", padx=3)

        dict_linha = {
            'frame': row_frame,
            'txt_busca': txt_busca,
            'cmb_ing': cmb_ing,
            'custo_parcial': 0.0,
            'produtos_encontrados': {}
        }

        btn_buscar = ctk.CTkButton(
            row_frame, text="🔍", width=35,
            command=lambda: self.buscar_ingredientes_db(txt_busca.get(), cmb_ing, dict_linha)
        )
        btn_buscar.pack(side="left", padx=2)

        txt_qtd = ctk.CTkEntry(row_frame, width=65, placeholder_text="Qtd")
        txt_qtd.pack(side="left", padx=3)
        if qtd > 0:
            txt_qtd.insert(0, f"{qtd:.2f}")

        cmb_un = ctk.CTkOptionMenu(row_frame, values=["kg", "g"], width=60)
        cmb_un.pack(side="left", padx=3)
        cmb_un.set(un)

        lbl_custo_info = ctk.CTkLabel(row_frame, text="R$ 0.00", font=("Arial", 11), width=130)
        lbl_custo_info.pack(side="left", padx=3)

        btn_remover = ctk.CTkButton(
            row_frame, text="X", width=30, fg_color="red", hover_color="darkred",
            command=lambda: self.remover_linha_ingrediente(dict_linha)
        )
        btn_remover.pack(side="left", padx=3)

        dict_linha.update({
            'txt_qtd': txt_qtd,
            'cmb_un': cmb_un,
            'lbl_custo': lbl_custo_info
        })

        if ing_id and desc:
            label_key = f"{desc} (ID: {ing_id})"
            dict_linha['produtos_encontrados'] = {
                label_key: {"id": ing_id, "pcompra": pcompra}
            }
            cmb_ing.configure(values=[label_key])
            cmb_ing.set(label_key)

        txt_qtd.bind("<KeyRelease>", lambda e: self.recalcular_linha(dict_linha))
        txt_busca.bind("<Return>", lambda e: self.buscar_ingredientes_db(txt_busca.get(), cmb_ing, dict_linha))
        cmb_ing.configure(command=lambda e: self.recalcular_linha(dict_linha))
        cmb_un.configure(command=lambda e: self.recalcular_linha(dict_linha))

        self.ingredientes_edit.append(dict_linha)
        self.recalcular_linha(dict_linha)

    def buscar_ingredientes_db(self, termo, cmb_widget, dict_linha):
        termo_clean = termo.strip()
        if not termo_clean:
            return

        try:
            with get_connection() as conn:
                cur = conn.cursor()

                if termo_clean.isdigit():
                    query = """
                        SELECT ID, DESCRICAO, PRECO_CUSTO FROM INGREDIENTE 
                        WHERE ID = ? OR UPPER(DESCRICAO) LIKE UPPER(?) 
                        ORDER BY DESCRICAO
                    """
                    cur.execute(query, (int(termo_clean), f"%{termo_clean}%"))
                else:
                    query = """
                        SELECT ID, DESCRICAO, PRECO_CUSTO FROM INGREDIENTE 
                        WHERE UPPER(DESCRICAO) LIKE UPPER(?) 
                        ORDER BY DESCRICAO
                    """
                    cur.execute(query, (f"%{termo_clean}%",))

                res = cur.fetchall()

            if not res:
                cmb_widget.configure(values=["Nenhum item encontrado"])
                dict_linha['produtos_encontrados'] = {}
                return

            dict_linha['produtos_encontrados'] = {
                f"{row[1]} (ID: {row[0]})": {
                    "id": int(row[0]),
                    "pcompra": float(row[2]) if row[2] is not None else 0.0
                } for row in res
            }

            opcoes = list(dict_linha['produtos_encontrados'].keys())
            cmb_widget.configure(values=opcoes)
            cmb_widget.set(opcoes[0])
            self.recalcular_linha(dict_linha)

        except Exception as e:
            messagebox.showerror("Erro de Banco", f"Erro ao pesquisar ingrediente:\n{e}", parent=self)

    def remover_linha_ingrediente(self, dict_linha):
        if dict_linha in self.ingredientes_edit:
            self.ingredientes_edit.remove(dict_linha)
            dict_linha['frame'].destroy()
            self.recalcular_custo_total()

    def recalcular_linha(self, dict_linha):
        prod_key = dict_linha['cmb_ing'].get()
        produtos = dict_linha.get('produtos_encontrados', {})

        if prod_key not in produtos:
            return

        pcompra = produtos[prod_key]['pcompra']
        try:
            qtd = float(dict_linha['txt_qtd'].get().replace(',', '.'))
            un = dict_linha['cmb_un'].get()

            fator = (qtd / 1000.0) if un == 'g' else qtd
            custo_parcial = fator * pcompra
            dict_linha['custo_parcial'] = custo_parcial

            dict_linha['lbl_custo'].configure(
                text=f"R$ {custo_parcial:.2f} (1kg=R$ {pcompra:.2f})"
            )
        except ValueError:
            dict_linha['custo_parcial'] = 0.0
            dict_linha['lbl_custo'].configure(text="R$ 0.00")

        self.recalcular_custo_total()

    def recalcular_custo_total(self):
        total = sum(item.get('custo_parcial', 0.0) for item in self.ingredientes_edit)
        self.lbl_custo_total.configure(text=f"Custo Total Calculado: R$ {total:.2f}")

    def salvar_receita(self):
        try:
            with get_connection() as conn:
                cur = conn.cursor()

                cur.execute("SELECT ID FROM PRODUTO_COMPOSTO WHERE PRODUTO_ID = ?", (int(self.produto_id),))
                comp_row = cur.fetchone()

                if not comp_row:
                    cur.execute("SELECT COALESCE(MAX(ID), 0) + 1 FROM PRODUTO_COMPOSTO")
                    composto_id = cur.fetchone()[0]
                    cur.execute("INSERT INTO PRODUTO_COMPOSTO (ID, PRODUTO_ID) VALUES (?, ?)", (composto_id, int(self.produto_id)))
                else:
                    composto_id = int(comp_row[0])
                    cur.execute("DELETE FROM FICHA_TECNICA WHERE COMPOSTO_ID = ?", (composto_id,))

                novo_custo_total = 0.0

                for dict_ing in self.ingredientes_edit:
                    prod_key = dict_ing['cmb_ing'].get()
                    produtos = dict_ing.get('produtos_encontrados', {})

                    if prod_key in produtos:
                        ingrediente_id = produtos[prod_key]['id']
                        qtd = float(dict_ing['txt_qtd'].get().replace(',', '.'))
                        un = dict_ing['cmb_un'].get()
                        pcompra = produtos[prod_key]['pcompra']

                        fator = (qtd / 1000.0) if un == 'g' else qtd
                        novo_custo_total += fator * pcompra

                        cur.execute("SELECT COALESCE(MAX(ID), 0) + 1 FROM FICHA_TECNICA")
                        novo_id_ft = cur.fetchone()[0]

                        cur.execute("""
                            INSERT INTO FICHA_TECNICA (ID, COMPOSTO_ID, INGREDIENTE_ID, QUANTIDADE, UNIDADE)
                            VALUES (?, ?, ?, ?, ?)
                        """, (novo_id_ft, composto_id, ingrediente_id, qtd, un))

                cur.execute("UPDATE PRODUTO SET PCOMPRA = ?, MODIF = CURRENT_TIMESTAMP WHERE ID = ?", (novo_custo_total, int(self.produto_id)))
                conn.commit()

            messagebox.showinfo("Sucesso", "Ficha técnica atualizada com sucesso!", parent=self)
            
            if self.on_close_callback:
                self.on_close_callback(novo_custo_total)

            self.destroy()

        except Exception as e:
            messagebox.showerror("Erro ao Salvar", f"Falha ao salvar receita:\n{e}", parent=self)


class AppSistema(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Gerenciador de Produtos e Receitas")
        self.geometry("1450x850")

        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.update() 

        janela_login = JanelaSenha(self, senha_correta="1989")
        self.wait_window(janela_login)

        if not janela_login.autenticado:
            self.destroy()
            return

        self.deiconify()

        inicializar_estrutura_banco()

        self.menu_frame = ctk.CTkFrame(self, height=50)
        self.menu_frame.pack(fill="x", side="top", padx=10, pady=5)

        self.btn_nav_consulta = ctk.CTkButton(self.menu_frame, text="Consulta de Cadastros", command=self.show_consulta)
        self.btn_nav_consulta.pack(side="left", padx=5, pady=10)

        self.btn_nav_create = ctk.CTkButton(self.menu_frame, text="Criar Produto / Receita", command=self.show_create)
        self.btn_nav_create.pack(side="left", padx=5, pady=10)

        self.btn_nav_notif = ctk.CTkButton(
            self.menu_frame,
            text="Notificações de Valores",
            command=self.show_notificacoes,
            image=None,
            anchor="w"
        )
        self.btn_nav_notif.configure(width=185)
        self.btn_nav_notif.pack(side="left", padx=5, pady=10)

        self.badge_notif = ctk.CTkLabel(
            master=self.btn_nav_notif,
            text="2",
            font=("Helvetica", 11, "bold"),
            text_color="white",
            fg_color="#E53935",
            width=40,
            height=25,
            corner_radius=10
        )
        self.badge_notif.place(relx=1.0, rely=0.5, x=6, y=8, anchor="center")

        self.btn_nav_ajuste = ctk.CTkButton(self.menu_frame, text="Valor de venda com (Frete/Comissão)", command=self.show_ajuste)
        self.btn_nav_ajuste.pack(side="left", padx=5, pady=10)

        self.btn_atualizar = ctk.CTkButton(
            self.menu_frame,
            text="🔄 Atualizar (F5)",
            command=self.atualizar_tela_atual,
            fg_color="#2B5B84",
            hover_color="#1F3F5C",
            font=("Arial", 12, "bold")
        )
        self.btn_atualizar.pack(side="right", padx=10, pady=10)

        self.bind_all("<F5>", lambda event: self.atualizar_tela_atual())

        self.container = ctk.CTkFrame(self)
        self.container.pack(fill="both", expand=True, padx=10, pady=5)

        self.frames = {}
        for PageClass in (TelaConsulta, TelaCadastroComposto, TelaNotificacoes, TelaAjusteVmax):
            page_name = PageClass.__name__
            frame = PageClass(parent=self.container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.current_frame_name = "TelaConsulta"
        self.piscar_estado = False
        self.qtd_notificacoes = 0
        self.hash_estoque_anterior = None

        self.show_consulta()
        self.verificar_alteracao_saida_estoque()
        self.atualizar_badge_notificacoes()
        self.loop_piscar_notificacao()

        self.after(100, self.verificar_estoque_minimo_inicial)
        self.after(3000, self.monitorar_estoque_automatico)

    def show_consulta(self):
        self.current_frame_name = "TelaConsulta"
        self.verificar_alteracao_saida_estoque()
        frame = self.frames["TelaConsulta"]
        frame.carregar_dados()
        frame.tkraise()

    def show_create(self):
        self.current_frame_name = "TelaCadastroComposto"
        frame = self.frames["TelaCadastroComposto"]
        frame.limpar_campos()
        frame.tkraise()

    def show_notificacoes(self):
        self.current_frame_name = "TelaNotificacoes"
        frame = self.frames["TelaNotificacoes"]
        frame.carregar_notificacoes()
        frame.tkraise()
        self.atualizar_badge_notificacoes()

    def show_ajuste(self):
        self.current_frame_name = "TelaAjusteVmax"
        self.verificar_alteracao_saida_estoque()
        frame = self.frames["TelaAjusteVmax"]
        frame.carregar_dados()
        frame.tkraise()

    def atualizar_tela_atual(self):
        """Método executado ao clicar no botão 'Atualizar' ou pressionar F5."""
        self.verificar_alteracao_saida_estoque()
        self.atualizar_badge_notificacoes()

        if self.current_frame_name == "TelaConsulta":
            self.frames["TelaConsulta"].carregar_dados()
        elif self.current_frame_name == "TelaNotificacoes":
            self.frames["TelaNotificacoes"].carregar_notificacoes()
        elif self.current_frame_name == "TelaAjusteVmax":
            self.frames["TelaAjusteVmax"].carregar_dados()

    def monitorar_estoque_automatico(self):
        """Verifica alterações externas na tabela ESTOQUE e INGREDIENTE para auto-atualizar a UI."""
        try:
            with get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT SUM(COALESCE(ESTOQEXP, 0)), COUNT(*) FROM ESTOQUE")
                res_est = cur.fetchone()
                cur.execute("SELECT SUM(COALESCE(ESTOQUE, 0)), COUNT(*) FROM INGREDIENTE")
                res_ing = cur.fetchone()

                hash_atual = f"{res_est[0]}_{res_est[1]}_{res_ing[0]}_{res_ing[1]}"

                if self.hash_estoque_anterior is not None and hash_atual != self.hash_estoque_anterior:
                    self.atualizar_tela_atual()

                self.hash_estoque_anterior = hash_atual
        except Exception as e:
            print(f"Aviso no monitor de estoque automático: {e}")

        self.after(3000, self.monitorar_estoque_automatico)

    def atualizar_badge_notificacoes(self):
        try:
            with get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM NOTIFICACAO_PRECO")
                self.qtd_notificacoes = cur.fetchone()[0] or 0

            if self.qtd_notificacoes > 0:
                self.badge_notif.configure(text=str(self.qtd_notificacoes))
                self.badge_notif.place(relx=0.88, rely=0.25, anchor="center")
                self.badge_notif.lift()
            else:
                self.badge_notif.place_forget()
        except Exception as e:
            print(f"Erro ao atualizar contagem de notificações: {e}")

    def loop_piscar_notificacao(self):
        self.atualizar_badge_notificacoes()
        if self.qtd_notificacoes > 0:
            if self.piscar_estado:
                self.badge_notif.configure(fg_color="#E53935")
            else:
                self.badge_notif.configure(fg_color="#78281F")
            self.piscar_estado = not self.piscar_estado
        
        self.after(2000, self.loop_piscar_notificacao)

    def verificar_estoque_minimo_inicial(self):
        itens_baixos = []
        try:
            with get_connection() as conn:
                cur = conn.cursor()

                query_prod = """
                    SELECT p.ESPEC, r.ESTOQEXP, r.ESTOQMIN
                    FROM ESTOQUE r
                    JOIN PRODUTO p ON p.ID = r.PRODUTO
                    WHERE r.ESTOQMIN > 0 AND r.ESTOQEXP <= r.ESTOQMIN
                """
                cur.execute(query_prod)
                for espec, est_atual, est_min in cur.fetchall():
                    est_a = float(est_atual) if est_atual is not None else 0.0
                    est_m = float(est_min) if est_min is not None else 0.0
                    itens_baixos.append(f"• [Produto Final] {espec} - Estoque: {est_a:.2f} UN (Mín: {est_m:.2f} UN)")

                query_ing = """
                    SELECT DESCRICAO, COALESCE(ESTOQUE, 0), COALESCE(ESTOQUEMIN, 0)
                    FROM INGREDIENTE
                    WHERE COALESCE(ESTOQUEMIN, 0) > 0 AND COALESCE(ESTOQUE, 0) <= COALESCE(ESTOQUEMIN, 0)
                """
                cur.execute(query_ing)
                for desc, est_atual, est_min in cur.fetchall():
                    est_a = float(est_atual) if est_atual is not None else 0.0
                    est_m = float(est_min) if est_min is not None else 0.0
                    itens_baixos.append(f"• [Ingrediente] {desc} - Estoque: {est_a:.2f} UN (Mín: {est_m:.2f} UN)")

            if itens_baixos:
                msg = "ATENÇÃO: Os seguintes itens estão acabando ou atingiram o estoque mínimo:\n\n" + "\n".join(itens_baixos)
                messagebox.showwarning("Alerta de Estoque Mínimo", msg)

        except Exception as e:
            print(f"Erro ao checar estoque mínimo inicial: {e}")

    def verificar_alteracao_saida_estoque(self):
        """
        Verifica se a quantia digitada no campo de estoque saiu (ou se o estoque zerou/ficou negativo)
        no outro processo e restaura o V.Max original no banco.
        """
        try:
            with get_connection() as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT r.PRODUTO_ID, r.VMAX_ORIGINAL, r.ESTOQUE_BASE, COALESCE(r.QTD_APLICADA, 0), COALESCE(e.ESTOQEXP, 0)
                    FROM REAJUSTE_TEMPORARIO r
                    LEFT JOIN ESTOQUE e ON e.PRODUTO = r.PRODUTO_ID
                """)
                reajustes = cur.fetchall()

                for prod_id, vmax_orig, est_base, qtd_aplicada, est_atual in reajustes:
                    est_b = float(est_base) if est_base is not None else 0.0
                    qtd_a = float(qtd_aplicada) if qtd_aplicada is not None else 0.0
                    est_a = float(est_atual) if est_atual is not None else 0.0
                    
                    if est_a <= (est_b - qtd_a) or est_a <= 0:
                        cur.execute("UPDATE PRODUTO SET PVENDA = ?, MODIF = CURRENT_TIMESTAMP WHERE ID = ?", (float(vmax_orig), int(prod_id)))
                        cur.execute("DELETE FROM REAJUSTE_TEMPORARIO WHERE PRODUTO_ID = ?", (int(prod_id),))

                conn.commit()
        except Exception as e:
            print(f"Erro ao verificar saída de estoque: {e}")


class TelaConsulta(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.selected_id = None

        self.frame_left = ctk.CTkFrame(self, width=550)
        self.frame_left.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        frame_sel = ctk.CTkFrame(self.frame_left)
        frame_sel.pack(fill="x", padx=10, pady=(10, 2))

        ctk.CTkLabel(frame_sel, text="Tabela Visualizada:", font=("Arial", 12, "bold")).pack(side="left", padx=5)
        self.cmb_tabela = ctk.CTkOptionMenu(
            frame_sel, 
            values=["Produtos Finais", "Ingredientes"],
            command=self.ao_mudar_tabela
        )
        self.cmb_tabela.pack(side="left", padx=5)

        self.lbl_busca = ctk.CTkLabel(self.frame_left, text="Pesquisar (Nome ou ID):")
        self.lbl_busca.pack(padx=10, pady=(10, 2), anchor="w")

        self.txt_busca = ctk.CTkEntry(self.frame_left, placeholder_text="Digite para filtrar...")
        self.txt_busca.pack(fill="x", padx=10, pady=5)
        self.txt_busca.bind("<KeyRelease>", self.filtrar_dados)

        self.tree = ttk.Treeview(
            self.frame_left, 
            columns=("ID", "ESPEC", "ESTOQUE", "ESTOQMIN", "PCOMPRA", "PREVENDA", "LUCRO_MIN", "PVENDA", "LUCRO_MAX"), 
            show="headings"
        )
        self.tree.heading("ID", text="ID")
        self.tree.heading("ESPEC", text="Descrição")
        self.tree.heading("ESTOQUE", text="Est. (UN)")
        self.tree.heading("ESTOQMIN", text="Mín. (UN)")
        self.tree.heading("PCOMPRA", text="Custo")
        self.tree.heading("PREVENDA", text="V. Mínimo")
        self.tree.heading("LUCRO_MIN", text="Lucro Mín.")
        self.tree.heading("PVENDA", text="V. Máximo")
        self.tree.heading("LUCRO_MAX", text="Lucro Máx.")

        self.tree.column("ID", width=35)
        self.tree.column("ESPEC", width=140)
        self.tree.column("ESTOQUE", width=55)
        self.tree.column("ESTOQMIN", width=55)
        self.tree.column("PCOMPRA", width=55)
        self.tree.column("PREVENDA", width=55)
        self.tree.column("LUCRO_MIN", width=60)
        self.tree.column("PVENDA", width=55)
        self.tree.column("LUCRO_MAX", width=60)

        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        self.tree.bind("<<TreeviewSelect>>", self.ao_selecionar_item)
        
        self.tree.bind("<Delete>", lambda event: self.deletar_registro())

        self.frame_right = ctk.CTkScrollableFrame(self, width=420)
        self.frame_right.pack(side="right", fill="both", padx=5, pady=5)

        self.lbl_detalhe = ctk.CTkLabel(self.frame_right, text="Edição do Registro - ID: -", font=("Arial", 16, "bold"))
        self.lbl_detalhe.pack(pady=(2, 5))

        ctk.CTkLabel(self.frame_right, text="Descrição:", font=("Arial", 11, "bold")).pack(anchor="w", padx=20, pady=(2, 0))
        self.entry_nome = ctk.CTkEntry(self.frame_right, height=28)
        self.entry_nome.pack(fill="x", padx=20, pady=1)

        self.lbl_est_atual = ctk.CTkLabel(self.frame_right, text="Estoque Atual (UN):", font=("Arial", 11, "bold"))
        self.entry_est_atual = ctk.CTkEntry(self.frame_right, height=28)

        self.lbl_est_min = ctk.CTkLabel(self.frame_right, text="Estoque Mínimo (UN):", font=("Arial", 11, "bold"))
        self.entry_est_min = ctk.CTkEntry(self.frame_right, height=28)

        self.frame_ingredientes_view = ctk.CTkFrame(self.frame_right)
        self.lbl_ing_titulo = ctk.CTkLabel(self.frame_ingredientes_view, text="Ingredientes / Receita", font=("Arial", 10, "bold"))
        self.lbl_ing_titulo.pack(pady=(1, 0))

        self.tree_ingredientes = ttk.Treeview(self.frame_ingredientes_view, columns=("ING", "QTD", "UN"), show="headings", height=3)
        self.tree_ingredientes.heading("ING", text="Ingrediente")
        self.tree_ingredientes.heading("QTD", text="Qtd")
        self.tree_ingredientes.heading("UN", text="Un")
        
        self.tree_ingredientes.column("ING", width=170)
        self.tree_ingredientes.column("QTD", width=50)
        self.tree_ingredientes.column("UN", width=35)
        self.tree_ingredientes.pack(fill="both", expand=True, padx=5, pady=2)

        self.btn_abrir_ficha = ctk.CTkButton(
            self.frame_right, text="🧪 Editar Receita / Ficha Técnica",
            command=self.abrir_janela_ficha_tecnica, fg_color="#1f538d", height=28, font=("Arial", 11, "bold")
        )

        self.lbl_custo_titulo = ctk.CTkLabel(self.frame_right, text="Custo (R$):", font=("Arial", 11, "bold"))
        self.entry_custo = ctk.CTkEntry(self.frame_right, height=28)
        self.entry_custo.bind("<KeyRelease>", self.ao_alterar_custo_manual)

        self.lbl_min = ctk.CTkLabel(self.frame_right, text="Valor Mínimo (R$):", font=("Arial", 11, "bold"))
        self.entry_min = ctk.CTkEntry(self.frame_right, height=28)
        self.entry_min.bind("<KeyRelease>", self.calcular_margens)

        self.lbl_lucro_min = ctk.CTkLabel(self.frame_right, text="Porcentagem Mínima: 0.00%", text_color="cyan", font=("Arial", 10, "bold"))

        self.lbl_max = ctk.CTkLabel(self.frame_right, text="Valor Máximo (R$):", font=("Arial", 11, "bold"))
        self.entry_max = ctk.CTkEntry(self.frame_right, height=28)
        self.entry_max.bind("<KeyRelease>", self.calcular_margens)

        self.lbl_lucro_max = ctk.CTkLabel(self.frame_right, text="Porcentagem Máxima: 0.00%", text_color="cyan", font=("Arial", 10, "bold"))

        self.btn_salvar = ctk.CTkButton(
            self.frame_right, text="Salvar Alterações", command=self.salvar_alteracoes,
            height=32, font=("Arial", 12, "bold"), fg_color="green"
        )

        self.btn_deletar = ctk.CTkButton(
            self.frame_right, text="Excluir Registro", command=self.deletar_registro,
            fg_color="red", hover_color="darkred", height=32, font=("Arial", 12, "bold")
        )

        self.montar_layout_edicao()

    def montar_layout_edicao(self):
        for w in [self.lbl_est_atual, self.entry_est_atual, self.lbl_est_min, self.entry_est_min,
                  self.btn_abrir_ficha, self.lbl_custo_titulo, self.entry_custo, 
                  self.lbl_min, self.entry_min, self.lbl_lucro_min, 
                  self.lbl_max, self.entry_max, self.lbl_lucro_max, 
                  self.btn_salvar, self.btn_deletar]:
            w.pack_forget()

        tabela = self.cmb_tabela.get()

        self.lbl_est_atual.pack(anchor="w", padx=20, pady=(3, 0))
        self.entry_est_atual.pack(fill="x", padx=20, pady=1)

        self.lbl_est_min.pack(anchor="w", padx=20, pady=(3, 0))
        self.entry_est_min.pack(fill="x", padx=20, pady=1)

        if tabela == "Produtos Finais":
            self.btn_abrir_ficha.pack(padx=20, pady=(6, 3), fill="x")

            self.lbl_custo_titulo.pack(anchor="w", padx=20, pady=(3, 0))
            self.entry_custo.pack(fill="x", padx=20, pady=1)

            self.lbl_min.pack(anchor="w", padx=20, pady=(3, 0))
            self.entry_min.pack(fill="x", padx=20, pady=1)
            self.lbl_lucro_min.pack(anchor="w", padx=20, pady=0)

            self.lbl_max.pack(anchor="w", padx=20, pady=(3, 0))
            self.entry_max.pack(fill="x", padx=20, pady=1)
            self.lbl_lucro_max.pack(anchor="w", padx=20, pady=0)
        else:
            self.lbl_custo_titulo.pack(anchor="w", padx=20, pady=(3, 0))
            self.entry_custo.pack(fill="x", padx=20, pady=1)

        self.btn_salvar.pack(pady=(10, 4), padx=20, fill="x")
        self.btn_deletar.pack(pady=(2, 8), padx=20, fill="x")

    def ao_mudar_tabela(self, escolha):
        self.limpar_campos_edicao()
        self.montar_layout_edicao()
        self.carregar_dados()

    def limpar_campos_edicao(self):
        self.selected_id = None
        self.lbl_detalhe.configure(text="Edição do Registro - ID: -")
        self.entry_nome.delete(0, 'end')
        self.entry_est_atual.delete(0, 'end')
        self.entry_est_min.delete(0, 'end')
        self.entry_custo.delete(0, 'end')
        self.entry_min.delete(0, 'end')
        self.entry_max.delete(0, 'end')
        self.lbl_lucro_min.configure(text="Porcentagem Mínima: 0.00%")
        self.lbl_lucro_max.configure(text="Porcentagem Máxima: 0.00%")
        self.ocultar_tabela_ingredientes()

    def ocultar_tabela_ingredientes(self):
        for row in self.tree_ingredientes.get_children():
            self.tree_ingredientes.delete(row)
        self.frame_ingredientes_view.pack_forget()

    def carregar_dados(self, filtro=""):
        for row in self.tree.get_children():
            self.tree.delete(row)

        tabela = self.cmb_tabela.get()
        filtro_clean = filtro.strip()

        try:
            with get_connection() as conn:
                cur = conn.cursor()

                if tabela == "Produtos Finais":
                    query_base = """
                        SELECT p.ID, p.ESPEC, COALESCE(e.ESTOQEXP, 0), COALESCE(e.ESTOQMIN, 0), p.PCOMPRA, p.PREVENDA, p.PVENDA 
                        FROM PRODUTO p
                        LEFT JOIN ESTOQUE e ON e.PRODUTO = p.ID
                    """
                    if filtro_clean:
                        if filtro_clean.isdigit():
                            query = query_base + " WHERE p.ID = ? OR UPPER(p.ESPEC) LIKE UPPER(?) ORDER BY p.ID DESC"
                            cur.execute(query, (int(filtro_clean), f"%{filtro_clean}%"))
                        else:
                            query = query_base + " WHERE UPPER(p.ESPEC) LIKE UPPER(?) ORDER BY p.ID DESC"
                            cur.execute(query, (f"%{filtro_clean}%",))
                    else:
                        query = query_base + " ORDER BY p.ID DESC"
                        cur.execute(query)

                    for row in cur.fetchall():
                        est_exp = float(row[2]) if row[2] is not None else 0.0
                        est_min = float(row[3]) if row[3] is not None else 0.0
                        pcompra = float(row[4]) if row[4] is not None else 0.0
                        prevenda = float(row[5]) if row[5] is not None else 0.0
                        pvenda = float(row[6]) if row[6] is not None else 0.0

                        lucro_max_rs = pvenda - pcompra

                        self.tree.insert("", "end", values=(
                            row[0], row[1] or "", f"{est_exp:.2f}", f"{est_min:.2f}", 
                            f"{pcompra:.2f}", f"{prevenda:.2f}", f"{lucro_min_rs:.2f}", 
                            f"{pvenda:.2f}", f"{lucro_max_rs:.2f}"
                        ))

                else:
                    query_base = "SELECT ID, DESCRICAO, COALESCE(ESTOQUE, 0), COALESCE(ESTOQUEMIN, 0), PRECO_CUSTO FROM INGREDIENTE"
                    if filtro_clean:
                        if filtro_clean.isdigit():
                            query = query_base + " WHERE ID = ? OR UPPER(DESCRICAO) LIKE UPPER(?) ORDER BY ID DESC"
                            cur.execute(query, (int(filtro_clean), f"%{filtro_clean}%"))
                        else:
                            query = query_base + " WHERE UPPER(DESCRICAO) LIKE UPPER(?) ORDER BY ID DESC"
                            cur.execute(query, (f"%{filtro_clean}%",))
                    else:
                        query = query_base + " ORDER BY ID DESC"
                        cur.execute(query)

                    for row in cur.fetchall():
                        est_exp = float(row[2]) if row[2] is not None else 0.0
                        est_min = float(row[3]) if row[3] is not None else 0.0
                        pcusto = float(row[4]) if row[4] is not None else 0.0
                        self.tree.insert("", "end", values=(
                            row[0], row[1] or "", f"{est_exp:.2f}", f"{est_min:.2f}", 
                            f"{pcusto:.2f}", "-", "-", "-", "-"
                        ))

        except Exception as e:
            messagebox.showerror("Erro de Banco de Dados", f"Falha ao carregar dados:\n{e}")

    def filtrar_dados(self, event=None):
        self.carregar_dados(self.txt_busca.get())

    def ao_selecionar_item(self, event):
        item = self.tree.selection()
        if not item:
            return
        vals = self.tree.item(item[0], "values")
        self.selected_id = int(vals[0])
        self.lbl_detalhe.configure(text=f"Edição do Registro - ID: {self.selected_id}")

        self.entry_nome.delete(0, 'end')
        self.entry_nome.insert(0, vals[1])

        self.entry_est_atual.delete(0, 'end')
        self.entry_est_atual.insert(0, vals[2])

        self.entry_est_min.delete(0, 'end')
        self.entry_est_min.insert(0, vals[3])

        self.entry_custo.delete(0, 'end')
        self.entry_custo.insert(0, vals[4])

        if self.cmb_tabela.get() == "Produtos Finais":
            self.entry_min.delete(0, 'end')
            self.entry_min.insert(0, vals[5])

            self.entry_max.delete(0, 'end')
            self.entry_max.insert(0, vals[7]) 

            self.calcular_margens()
            self.carregar_ingredientes_produto(self.selected_id)

    def carregar_ingredientes_produto(self, produto_id):
        self.ocultar_tabela_ingredientes()

        try:
            with get_connection() as conn:
                cur = conn.cursor()
                query = """
                    SELECT i.DESCRICAO, ft.QUANTIDADE, ft.UNIDADE
                    FROM PRODUTO_COMPOSTO pc
                    JOIN FICHA_TECNICA ft ON ft.COMPOSTO_ID = pc.ID
                    JOIN INGREDIENTE i ON i.ID = ft.INGREDIENTE_ID
                    WHERE pc.PRODUTO_ID = ?
                """
                cur.execute(query, (int(produto_id),))
                rows = cur.fetchall()

            if rows:
                for row in rows:
                    qtd = float(row[1]) if row[1] is not None else 0.0
                    self.tree_ingredientes.insert("", "end", values=(row[0], f"{qtd:.2f}", row[2]))
                
                self.frame_ingredientes_view.pack(after=self.entry_est_min, fill="x", padx=20, pady=3)

        except Exception as e:
            print(f"Erro ao carregar ingredientes: {e}")

    def abrir_janela_ficha_tecnica(self):
        if not self.selected_id or self.cmb_tabela.get() != "Produtos Finais":
            messagebox.showwarning("Atenção", "Selecione um produto da lista para editar a receita!")
            return

        nome_prod = self.entry_nome.get()

        def callback_atualizacao(novo_custo):
            self.entry_custo.delete(0, 'end')
            self.entry_custo.insert(0, f"{novo_custo:.2f}")
            self.ao_alterar_custo_manual()
            self.carregar_dados()
            self.carregar_ingredientes_produto(self.selected_id)

        JanelaEdicaoFichaTecnica(
            parent=self,
            produto_id=self.selected_id,
            produto_nome=nome_prod,
            on_close_callback=callback_atualizacao
        )

    def ao_alterar_custo_manual(self, event=None):
        if self.cmb_tabela.get() != "Produtos Finais":
            return
        try:
            texto_custo = self.entry_custo.get().replace(',', '.').strip()
            if texto_custo:
                custo = float(texto_custo)
                v_min = custo + 8.00
                v_max = v_min + 10.00

                self.entry_min.delete(0, 'end')
                self.entry_min.insert(0, f"{v_min:.2f}")

                self.entry_max.delete(0, 'end')
                self.entry_max.insert(0, f"{v_max:.2f}")
        except ValueError:
            pass

        self.calcular_margens()

    def calcular_margens(self, event=None):
        if self.cmb_tabela.get() != "Produtos Finais":
            return
        try:
            custo = float(self.entry_custo.get().replace(',', '.'))
            v_min = float(self.entry_min.get().replace(',', '.'))
            v_max = float(self.entry_max.get().replace(',', '.'))

            if custo > 0:
                lucro_min = ((v_min - custo) / custo) * 100
                lucro_max = ((v_max - custo) / custo) * 100
                self.lbl_lucro_min.configure(text=f"Porcentagem Mínima: {lucro_min:.2f}%")
                self.lbl_lucro_max.configure(text=f"Porcentagem Máxima: {lucro_max:.2f}%")
            else:
                self.lbl_lucro_min.configure(text="Porcentagem Mínima: -")
                self.lbl_lucro_max.configure(text="Porcentagem Máxima: -")
        except ValueError:
            pass

    def salvar_alteracoes(self):
        if not self.selected_id:
            messagebox.showwarning("Atenção", "Selecione um registro para salvar.")
            return

        tabela = self.cmb_tabela.get()

        try:
            est_atual = float(self.entry_est_atual.get().replace(',', '.').strip() or 0)
        except ValueError:
            est_atual = 0.0

        try:
            est_min = float(self.entry_est_min.get().replace(',', '.').strip() or 0)
        except ValueError:
            est_min = 0.0

        try:
            with get_connection() as conn:
                cur = conn.cursor()
                nome = self.entry_nome.get().strip()

                if tabela == "Produtos Finais":
                    custo = float(self.entry_custo.get().replace(',', '.'))
                    v_min = float(self.entry_min.get().replace(',', '.'))
                    v_max = float(self.entry_max.get().replace(',', '.'))

                    if v_min < custo:
                        messagebox.showerror("Erro de Validação", "O Valor Mínimo não pode ser menor que o Custo!")
                        return
                    if v_max < v_min:
                        messagebox.showerror("Erro de Validação", "O Valor Máximo não pode ser menor que o Valor Mínimo!")
                        return

                    cur.execute("SELECT ID FROM PRODUTO WHERE UPPER(ESPEC) = UPPER(?) AND ID <> ?", (nome, int(self.selected_id)))
                    if cur.fetchone():
                        messagebox.showerror("Erro de Duplicidade", f"Já existe outro produto cadastrado como '{nome}'!")
                        return

                    cur.execute("""
                        UPDATE PRODUTO 
                        SET ESPEC = ?, PCOMPRA = ?, PREVENDA = ?, PVENDA = ?, MODIF = CURRENT_TIMESTAMP
                        WHERE ID = ?
                    """, (nome, custo, v_min, v_max, int(self.selected_id)))

                    cur.execute("SELECT FIRMA FROM ESTOQUE WHERE PRODUTO = ?", (int(self.selected_id),))
                    if cur.fetchone():
                        cur.execute("""
                            UPDATE ESTOQUE 
                            SET ESTOQEXP = ?, ESTOQMIN = ?
                            WHERE PRODUTO = ?
                        """, (est_atual, est_min, int(self.selected_id)))
                    else:
                        cur.execute("""
                            INSERT INTO ESTOQUE (FIRMA, PRODUTO, ESTOQEXP, ESTOQMIN, ESTOQDEP, ESTOQCSM, ESTOQTFM, ESTOQANT, ESTOQAUD, SITUACAO, UAUDIT)
                            VALUES (1, ?, ?, ?, 0, 0, 0, 0, 0, 0, NULL)
                        """, (int(self.selected_id), est_atual, est_min))

                    conn.commit()
                    messagebox.showinfo("Sucesso", "Alterações salvas com sucesso!")

                else:
                    custo = float(self.entry_custo.get().replace(',', '.'))

                    cur.execute("SELECT ID FROM INGREDIENTE WHERE UPPER(DESCRICAO) = UPPER(?) AND ID <> ?", (nome, int(self.selected_id)))
                    if cur.fetchone():
                        messagebox.showerror("Erro de Duplicidade", f"Já existe outro ingrediente cadastrado como '{nome}'!")
                        return

                    cur.execute("""
                        UPDATE INGREDIENTE 
                        SET DESCRICAO = ?, PRECO_CUSTO = ?, ESTOQUE = ?, ESTOQUEMIN = ?
                        WHERE ID = ?
                    """, (nome, custo, est_atual, est_min, int(self.selected_id)))

                    conn.commit()

            if tabela == "Ingredientes":
                self.recalcular_produtos_compostos(int(self.selected_id))
                self.controller.show_notificacoes()

            self.carregar_dados()

        except Exception as e:
            messagebox.showerror("Erro", str(e))

    def recalcular_produtos_compostos(self, ingrediente_id):
        produtos_alterados = []
        try:
            with get_connection() as conn:
                cur = conn.cursor()

                cur.execute("SELECT DISTINCT COMPOSTO_ID FROM FICHA_TECNICA WHERE INGREDIENTE_ID = ?", (int(ingrediente_id),))
                compostos = cur.fetchall()

                for (comp_id,) in compostos:
                    cur.execute("""
                        SELECT ft.QUANTIDADE, ft.UNIDADE, i.PRECO_CUSTO 
                        FROM FICHA_TECNICA ft
                        JOIN INGREDIENTE i ON i.ID = ft.INGREDIENTE_ID
                        WHERE ft.COMPOSTO_ID = ?
                    """, (int(comp_id),))

                    novo_custo_total = 0.0
                    for qtd, unid, pcusto in cur.fetchall():
                        pcusto = float(pcusto) if pcusto is not None else 0.0
                        qtd = float(qtd) if qtd is not None else 0.0
                        fator = (qtd / 1000.0) if str(unid).lower() == 'g' else qtd
                        novo_custo_total += fator * pcusto

                    cur.execute("""
                        SELECT PRODUTO_ID, PREVENDA, PVENDA, PCOMPRA, ESPEC 
                        FROM PRODUTO p
                        JOIN PRODUTO_COMPOSTO pc ON pc.PRODUTO_ID = p.ID
                        WHERE pc.ID = ?
                    """, (int(comp_id),))
                    prod_data = cur.fetchone()

                    if prod_data:
                        prod_id = int(prod_data[0])
                        prevenda_atual = float(prod_data[1]) if prod_data[1] is not None else 0.0
                        pvenda_atual = float(prod_data[2]) if prod_data[2] is not None else 0.0
                        pcompra_ant = float(prod_data[3]) if prod_data[3] is not None else 0.0
                        espec_prod = prod_data[4] or f"ID {prod_id}"

                        novo_min = prevenda_atual
                        if novo_min < novo_custo_total:
                            novo_min = novo_custo_total + 8.00

                        novo_max = pvenda_atual
                        if novo_max < novo_min:
                            novo_max = novo_min + 10.00

                        cur.execute("SELECT COALESCE(MAX(ID), 0) + 1 FROM NOTIFICACAO_PRECO")
                        novo_notif_id = cur.fetchone()[0]

                        cur.execute("""
                            INSERT INTO NOTIFICACAO_PRECO (ID, PRODUTO_ID, CUSTO_ANT, VMIN_ANT, VMAX_ANT, CUSTO_ATU, VMIN_ATU, VMAX_ATU)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (novo_notif_id, prod_id, pcompra_ant, prevenda_atual, pvenda_atual, novo_custo_total, novo_min, novo_max))

                        cur.execute("""
                            UPDATE PRODUTO 
                            SET PCOMPRA = ?, PREVENDA = ?, PVENDA = ?, MODIF = CURRENT_TIMESTAMP
                            WHERE ID = ?
                        """, (novo_custo_total, novo_min, novo_max, prod_id))

                        produtos_alterados.append(
                            f"• {espec_prod}\n  Custo: R$ {pcompra_ant:.2f} ➔ R$ {novo_custo_total:.2f}\n  V.Max: R$ {pvenda_atual:.2f} ➔ R$ {novo_max:.2f}"
                        )

                conn.commit()

            if produtos_alterados:
                msg = "A alteração do ingrediente atualizou os seguintes produtos:\n\n" + "\n\n".join(produtos_alterados)
                messagebox.showinfo("Produtos Atualizados", msg)

        except Exception as e:
            print(f"Erro ao recalcular produtos compostos: {e}")

    def deletar_registro(self):
        if not self.selected_id:
            messagebox.showwarning("Atenção", "Selecione um registro para excluir.")
            return

        tabela = self.cmb_tabela.get()
        nome = self.entry_nome.get()

        if not messagebox.askyesno("Confirmar Exclusão", f"Tem certeza que deseja excluir o item abaixo?\n\nID: {self.selected_id}\nDescrição: {nome}"):
            return

        try:
            with get_connection() as conn:
                cur = conn.cursor()

                if tabela == "Ingredientes":
                    cur.execute("SELECT COUNT(*) FROM FICHA_TECNICA WHERE INGREDIENTE_ID = ?", (int(self.selected_id),))
                    qtd_vinculos = cur.fetchone()[0]

                    if qtd_vinculos > 0:
                        messagebox.showerror(
                            "Impossível Excluir",
                            f"Este ingrediente é utilizado em {qtd_vinculos} receita(s)!\n"
                            "Remova-o das fichas técnicas antes de excluí-lo."
                        )
                        return

                    cur.execute("DELETE FROM INGREDIENTE WHERE ID = ?", (int(self.selected_id),))

                else:
                    cur.execute("DELETE FROM ESTOQUE WHERE PRODUTO = ?", (int(self.selected_id),))

                    cur.execute("SELECT ID FROM PRODUTO_COMPOSTO WHERE PRODUTO_ID = ?", (int(self.selected_id),))
                    comp = cur.fetchone()

                    if comp:
                        comp_id = int(comp[0])
                        cur.execute("DELETE FROM FICHA_TECNICA WHERE COMPOSTO_ID = ?", (comp_id,))
                        cur.execute("DELETE FROM PRODUTO_COMPOSTO WHERE ID = ?", (comp_id,))

                    cur.execute("DELETE FROM NOTIFICACAO_PRECO WHERE PRODUTO_ID = ?", (int(self.selected_id),))
                    cur.execute("DELETE FROM REAJUSTE_TEMPORARIO WHERE PRODUTO_ID = ?", (int(self.selected_id),))
                    cur.execute("DELETE FROM PRODUTO WHERE ID = ?", (int(self.selected_id),))

                conn.commit()

            messagebox.showinfo("Sucesso", "Registro excluído com sucesso!")
            self.limpar_campos_edicao()
            self.carregar_dados()

        except Exception as e:
            messagebox.showerror("Erro de Exclusão", f"Falha ao excluir:\n{e}")


class TelaNotificacoes(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        ctk.CTkLabel(self, text="Notificações de Alteração de Valores", font=("Arial", 18, "bold")).pack(pady=10)

        self.scroll_notif = ctk.CTkScrollableFrame(self)
        self.scroll_notif.pack(fill="both", expand=True, padx=20, pady=10)

    def carregar_notificacoes(self):
        for widget in self.scroll_notif.winfo_children():
            widget.destroy()

        try:
            with get_connection() as conn:
                cur = conn.cursor()
                query = """
                    SELECT n.ID, n.PRODUTO_ID, p.ESPEC, n.CUSTO_ANT, n.VMIN_ANT, n.VMAX_ANT,
                           n.CUSTO_ATU, n.VMIN_ATU, n.VMAX_ATU
                    FROM NOTIFICACAO_PRECO n
                    JOIN PRODUTO p ON p.ID = n.PRODUTO_ID
                    ORDER BY n.ID DESC
                """
                cur.execute(query)
                notifs = cur.fetchall()

            if not notifs:
                ctk.CTkLabel(self.scroll_notif, text="Nenhuma notificação de alteração de valor pendente.", font=("Arial", 14)).pack(pady=20)
                self.controller.atualizar_badge_notificacoes()
                return

            for notif in notifs:
                notif_id, prod_id, espec, c_ant, min_ant, max_ant, c_atu, min_atu, max_atu = notif
                self.criar_card_notificacao(
                    notif_id, prod_id, espec or "",
                    float(c_ant or 0), float(min_ant or 0), float(max_ant or 0),
                    float(c_atu or 0), float(min_atu or 0), float(max_atu or 0)
                )

        except Exception as e:
            messagebox.showerror("Erro de Banco", f"Erro ao carregar notificações:\n{e}")

    def criar_card_notificacao(self, notif_id, prod_id, desc, c_ant, min_ant, max_ant, c_atu, min_atu, max_atu):
        card = ctk.CTkFrame(self.scroll_notif)
        card.pack(fill="x", pady=6, padx=5)

        f_linha1 = ctk.CTkFrame(card, fg_color="transparent")
        f_linha1.pack(fill="x", padx=5, pady=2)

        ctk.CTkLabel(f_linha1, text=f"{desc}", font=("Arial", 12, "bold"), width=200, anchor="w").pack(side="left", padx=5)
        ctk.CTkLabel(f_linha1, text=f"custo anterior: R$ {c_ant:.2f}", width=140).pack(side="left", padx=5)
        ctk.CTkLabel(f_linha1, text=f"v.min. anterior: R$ {min_ant:.2f}", width=140).pack(side="left", padx=5)
        ctk.CTkLabel(f_linha1, text=f"v. max. anterior: R$ {max_ant:.2f}", width=140).pack(side="left", padx=5)

        f_linha2 = ctk.CTkFrame(card, fg_color="transparent")
        f_linha2.pack(fill="x", padx=5, pady=4)

        ctk.CTkLabel(f_linha2, text=f"{desc}", font=("Arial", 12, "bold"), width=200, anchor="w").pack(side="left", padx=5)

        ctk.CTkLabel(f_linha2, text="custo atual:").pack(side="left", padx=2)
        txt_custo = ctk.CTkEntry(f_linha2, width=80)
        txt_custo.insert(0, f"{c_atu:.2f}")
        txt_custo.pack(side="left", padx=5)

        ctk.CTkLabel(f_linha2, text="v.min atual:").pack(side="left", padx=2)
        txt_min = ctk.CTkEntry(f_linha2, width=80)
        txt_min.insert(0, f"{min_atu:.2f}")
        txt_min.pack(side="left", padx=5)

        ctk.CTkLabel(f_linha2, text="v.max. atual:").pack(side="left", padx=2)
        txt_max = ctk.CTkEntry(f_linha2, width=80)
        txt_max.insert(0, f"{max_atu:.2f}")
        txt_max.pack(side="left", padx=5)

        btn_salvar = ctk.CTkButton(
            f_linha2, text="Salvar", width=65, fg_color="green",
            command=lambda: self.salvar_notificacao(notif_id, prod_id, txt_custo.get(), txt_min.get(), txt_max.get(), card)
        )
        btn_salvar.pack(side="left", padx=5)

        btn_excluir = ctk.CTkButton(
            f_linha2, text="Excluir", width=65, fg_color="red", hover_color="darkred",
            command=lambda: self.excluir_notificacao(notif_id, card)
        )
        btn_excluir.pack(side="left", padx=5)

    def salvar_notificacao(self, notif_id, prod_id, c_str, min_str, max_str, card_widget):
        try:
            custo = float(c_str.replace(',', '.'))
            v_min = float(min_str.replace(',', '.'))
            v_max = float(max_str.replace(',', '.'))

            if v_min < custo:
                messagebox.showerror("Erro", "O Valor Mínimo não pode ser menor que o Custo!")
                return
            if v_max < v_min:
                messagebox.showerror("Erro", "O Valor Máximo não pode ser menor que o Valor Mínimo!")
                return

            with get_connection() as conn:
                cur = conn.cursor()
                cur.execute("""
                    UPDATE PRODUTO 
                    SET PCOMPRA = ?, PREVENDA = ?, PVENDA = ?, MODIF = CURRENT_TIMESTAMP
                    WHERE ID = ?
                """, (custo, v_min, v_max, int(prod_id)))

                cur.execute("DELETE FROM NOTIFICACAO_PRECO WHERE ID = ?", (int(notif_id),))
                conn.commit()

            messagebox.showinfo("Sucesso", "Valores do produto atualizados e notificação encerrada!")
            card_widget.destroy()
            self.controller.atualizar_badge_notificacoes()

        except ValueError:
            messagebox.showerror("Erro", "Insira valores numéricos válidos.")
        except Exception as e:
            messagebox.showerror("Erro ao Salvar", str(e))

    def excluir_notificacao(self, notif_id, card_widget):
        try:
            with get_connection() as conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM NOTIFICACAO_PRECO WHERE ID = ?", (int(notif_id),))
                conn.commit()

            card_widget.destroy()
            self.controller.atualizar_badge_notificacoes()
        except Exception as e:
            messagebox.showerror("Erro de Exclusão", str(e))


class TelaAjusteVmax(ctk.CTkFrame):
    """Tela de Ajuste V.Max reformulada"""
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.selected_id = None
        self.vmax_original_db = 0.0
        self.estoque_disponivel = 0.0

        self.frame_left = ctk.CTkFrame(self, width=550)
        self.frame_left.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        self.lbl_busca = ctk.CTkLabel(self.frame_left, text="Pesquisar Produto Final (Nome ou ID):")
        self.lbl_busca.pack(padx=10, pady=(10, 2), anchor="w")

        self.txt_busca = ctk.CTkEntry(self.frame_left, placeholder_text="Digite para filtrar...")
        self.txt_busca.pack(fill="x", padx=10, pady=5)
        self.txt_busca.bind("<KeyRelease>", lambda e: self.carregar_dados(self.txt_busca.get()))

        self.tree = ttk.Treeview(self.frame_left, columns=("ID", "ESPEC", "ESTOQUE", "PVENDA"), show="headings")
        self.tree.heading("ID", text="ID")
        self.tree.heading("ESPEC", text="Descrição")
        self.tree.heading("ESTOQUE", text="Est. (UN)")
        self.tree.heading("PVENDA", text="V. Max Atual")

        self.tree.column("ID", width=40)
        self.tree.column("ESPEC", width=220)
        self.tree.column("ESTOQUE", width=80)
        self.tree.column("PVENDA", width=90)

        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        self.tree.bind("<<TreeviewSelect>>", self.ao_selecionar_item)

        self.frame_right = ctk.CTkScrollableFrame(self, width=420)
        self.frame_right.pack(side="right", fill="both", padx=5, pady=5)

        self.lbl_detalhe = ctk.CTkLabel(self.frame_right, text="Ajuste de V.Max - ID: -", font=("Arial", 16, "bold"))
        self.lbl_detalhe.pack(pady=(10, 5))

        ctk.CTkLabel(self.frame_right, text="Descrição:", font=("Arial", 11, "bold")).pack(anchor="w", padx=20, pady=(5, 0))
        self.lbl_nome = ctk.CTkLabel(self.frame_right, text="-", font=("Arial", 12), text_color="yellow")
        self.lbl_nome.pack(anchor="w", padx=20, pady=2)

        ctk.CTkLabel(self.frame_right, text="V. Max Base (Unid. R$):", font=("Arial", 11, "bold")).pack(anchor="w", padx=20, pady=(5, 0))
        self.entry_vmax_ant = ctk.CTkEntry(self.frame_right, height=28)
        self.entry_vmax_ant.pack(fill="x", padx=20, pady=1)
        self.entry_vmax_ant.bind("<KeyRelease>", self.recalcular_total)

        ctk.CTkLabel(self.frame_right, text="Qtd. Saída Estoque Limite (UN):", font=("Arial", 11, "bold")).pack(anchor="w", padx=20, pady=(5, 0))
        self.entry_qtd_est = ctk.CTkEntry(self.frame_right, height=28)
        self.entry_qtd_est.pack(fill="x", padx=20, pady=1)
        self.entry_qtd_est.bind("<KeyRelease>", self.recalcular_total)

        ctk.CTkLabel(self.frame_right, text="Frete por Unidade (R$):", font=("Arial", 11, "bold")).pack(anchor="w", padx=20, pady=(5, 0))
        self.entry_frete = ctk.CTkEntry(self.frame_right, height=28)
        self.entry_frete.pack(fill="x", padx=20, pady=1)
        self.entry_frete.bind("<KeyRelease>", self.recalcular_total)

        ctk.CTkLabel(self.frame_right, text="Comissão por Unidade (R$):", font=("Arial", 11, "bold")).pack(anchor="w", padx=20, pady=(5, 0))
        self.entry_comissao = ctk.CTkEntry(self.frame_right, height=28)
        self.entry_comissao.pack(fill="x", padx=20, pady=1)
        self.entry_comissao.bind("<KeyRelease>", self.recalcular_total)

        self.lbl_total_vmax = ctk.CTkLabel(
            self.frame_right, text="Novo V.Max Unitário: R$ 0.00", font=("Arial", 13, "bold"), text_color="cyan"
        )
        self.lbl_total_vmax.pack(pady=15)

        self.btn_salvar = ctk.CTkButton(
            self.frame_right, text="Salvar Ajuste Temporário", command=self.salvar_ajuste,
            height=35, font=("Arial", 12, "bold"), fg_color="green"
        )
        self.btn_salvar.pack(pady=10, padx=20, fill="x")

    def carregar_dados(self, filtro=""):
        for row in self.tree.get_children():
            self.tree.delete(row)

        filtro_clean = filtro.strip()
        try:
            with get_connection() as conn:
                cur = conn.cursor()
                query_base = """
                    SELECT p.ID, p.ESPEC, COALESCE(e.ESTOQEXP, 0), p.PVENDA
                    FROM PRODUTO p
                    LEFT JOIN ESTOQUE e ON e.PRODUTO = p.ID
                """
                if filtro_clean:
                    if filtro_clean.isdigit():
                        query = query_base + " WHERE p.ID = ? OR UPPER(p.ESPEC) LIKE UPPER(?) ORDER BY p.ID DESC"
                        cur.execute(query, (int(filtro_clean), f"%{filtro_clean}%"))
                    else:
                        query = query_base + " WHERE UPPER(p.ESPEC) LIKE UPPER(?) ORDER BY p.ID DESC"
                        cur.execute(query, (f"%{filtro_clean}%",))
                else:
                    query = query_base + " ORDER BY p.ID DESC"
                    cur.execute(query)

                for row in cur.fetchall():
                    est_exp = float(row[2]) if row[2] is not None else 0.0
                    pvenda = float(row[3]) if row[3] is not None else 0.0
                    self.tree.insert("", "end", values=(row[0], row[1] or "", f"{est_exp:.2f}", f"{pvenda:.2f}"))

        except Exception as e:
            messagebox.showerror("Erro de Banco", f"Erro ao carregar dados:\n{e}")

    def ao_selecionar_item(self, event):
        item = self.tree.selection()
        if not item:
            return
        vals = self.tree.item(item[0], "values")
        self.selected_id = int(vals[0])
        self.lbl_detalhe.configure(text=f"Ajuste de V.Max - ID: {self.selected_id}")
        self.lbl_nome.configure(text=vals[1])

        self.estoque_disponivel = float(vals[2])
        vmax_atual = float(vals[3])
        self.vmax_original_db = vmax_atual

        self.entry_vmax_ant.delete(0, 'end')
        self.entry_vmax_ant.insert(0, f"{vmax_atual:.2f}")

        frete_salvo, com_salva, qtd_aplicada = 0.0, 0.0, self.estoque_disponivel
        try:
            with get_connection() as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT VMAX_ORIGINAL, FRETE_UNIT, COMISSAO_UNIT, QTD_APLICADA 
                    FROM REAJUSTE_TEMPORARIO WHERE PRODUTO_ID = ?
                """, (int(self.selected_id),))
                row = cur.fetchone()
                if row:
                    vmax_orig, frete_salvo, com_salva, qtd_aplicada = row
                    self.vmax_original_db = float(vmax_orig)
                    self.entry_vmax_ant.delete(0, 'end')
                    self.entry_vmax_ant.insert(0, f"{float(vmax_orig):.2f}")
        except Exception:
            pass

        self.entry_qtd_est.delete(0, 'end')
        self.entry_qtd_est.insert(0, f"{float(qtd_aplicada):.2f}")

        self.entry_frete.delete(0, 'end')
        self.entry_frete.insert(0, f"{float(frete_salvo):.2f}")

        self.entry_comissao.delete(0, 'end')
        self.entry_comissao.insert(0, f"{float(com_salva):.2f}")

        self.recalcular_total()

    def recalcular_total(self, event=None):
        try:
            val_base_str = self.entry_vmax_ant.get().replace(',', '.').strip()
            vmax_base = float(val_base_str) if val_base_str else 0.0
            frete = float(self.entry_frete.get().replace(',', '.')) if self.entry_frete.get().strip() else 0.0
            comissao = float(self.entry_comissao.get().replace(',', '.')) if self.entry_comissao.get().strip() else 0.0

            novo_vmax_unitario = vmax_base + frete + comissao
            self.lbl_total_vmax.configure(text=f"Novo V.Max Unitário: R$ {novo_vmax_unitario:.2f}")
        except ValueError:
            self.lbl_total_vmax.configure(text="Novo V.Max Unitário: R$ -")

    def salvar_ajuste(self):
        if not self.selected_id:
            messagebox.showwarning("Atenção", "Selecione um produto final na tabela para aplicar o ajuste.")
            return

        try:
            val_base_str = self.entry_vmax_ant.get().replace(',', '.').strip()
            vmax_base = float(val_base_str) if val_base_str else 0.0
            qtd_aplicada = float(self.entry_qtd_est.get().replace(',', '.'))
            frete_unit = float(self.entry_frete.get().replace(',', '.')) if self.entry_frete.get().strip() else 0.0
            com_unit = float(self.entry_comissao.get().replace(',', '.')) if self.entry_comissao.get().strip() else 0.0

            vmax_temp = vmax_base + frete_unit + com_unit

            with get_connection() as conn:
                cur = conn.cursor()

                cur.execute("UPDATE PRODUTO SET PVENDA = ?, MODIF = CURRENT_TIMESTAMP WHERE ID = ?", (vmax_temp, int(self.selected_id)))

                cur.execute("SELECT PRODUTO_ID FROM REAJUSTE_TEMPORARIO WHERE PRODUTO_ID = ?", (int(self.selected_id),))
                if cur.fetchone():
                    cur.execute("""
                        UPDATE REAJUSTE_TEMPORARIO
                        SET VMAX_ORIGINAL = ?, FRETE_UNIT = ?, COMISSAO_UNIT = ?, VMAX_TEMPORARIO = ?, ESTOQUE_BASE = ?, QTD_APLICADA = ?
                        WHERE PRODUTO_ID = ?
                    """, (self.vmax_original_db, frete_unit, com_unit, vmax_temp, float(self.estoque_disponivel), qtd_aplicada, int(self.selected_id)))
                else:
                    cur.execute("""
                        INSERT INTO REAJUSTE_TEMPORARIO (PRODUTO_ID, VMAX_ORIGINAL, FRETE_UNIT, COMISSAO_UNIT, VMAX_TEMPORARIO, ESTOQUE_BASE, QTD_APLICADA)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (int(self.selected_id), self.vmax_original_db, frete_unit, com_unit, vmax_temp, float(self.estoque_disponivel), qtd_aplicada))

                conn.commit()

            messagebox.showinfo("Sucesso", "Ajuste temporário de V.Max salvo com sucesso!")
            self.carregar_dados()

        except ValueError:
            messagebox.showerror("Erro", "Verifique se digitou números válidos nos campos.")
        except Exception as e:
            messagebox.showerror("Erro ao Salvar", str(e))


class TelaCadastroComposto(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.ingredientes_linhas = []

        ctk.CTkLabel(self, text="Cadastro de Novo Item / Receita", font=("Arial", 18, "bold")).pack(pady=10)

        frame_top = ctk.CTkFrame(self)
        frame_top.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(frame_top, text="Descrição:").grid(row=0, column=0, padx=5, pady=5)
        self.txt_nome_base = ctk.CTkEntry(frame_top, width=200)
        self.txt_nome_base.grid(row=0, column=1, padx=5, pady=5)
        self.txt_nome_base.bind("<KeyRelease>", self.atualizar_sugestao)

        ctk.CTkLabel(frame_top, text="Peso:").grid(row=0, column=2, padx=5, pady=5)
        self.txt_peso = ctk.CTkEntry(frame_top, width=80)
        self.txt_peso.grid(row=0, column=3, padx=5, pady=5)
        self.txt_peso.bind("<KeyRelease>", self.atualizar_sugestao)

        self.cmb_unidade = ctk.CTkOptionMenu(frame_top, values=["kg", "g"], command=lambda x: self.atualizar_sugestao())
        self.cmb_unidade.grid(row=0, column=4, padx=5, pady=5)

        self.lbl_sugestao = ctk.CTkLabel(self, text="Como irá ficar a descrição: -", font=("Arial", 13, "bold"), text_color="yellow")
        self.lbl_sugestao.pack(pady=5)

        self.frame_ingredientes = ctk.CTkScrollableFrame(self, height=220, label_text="Ingredientes da Receita (Se vazio, será cadastrado como Ingrediente)")
        self.frame_ingredientes.pack(fill="both", expand=True, padx=20, pady=10)

        self.btn_add_ing = ctk.CTkButton(self, text="+ Adicionar Ingrediente", command=self.adicionar_linha_ingrediente)
        self.btn_add_ing.pack(pady=5)

        self.lbl_custo_total = ctk.CTkLabel(self, text="Custo total do item: R$ 0.00", font=("Arial", 14, "bold"))
        self.lbl_custo_total.pack(pady=5)

        frame_preco = ctk.CTkFrame(self)
        frame_preco.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(frame_preco, text="Estoque (UN):").grid(row=0, column=0, padx=3, pady=5)
        self.txt_estoque_atual = ctk.CTkEntry(frame_preco, width=75)
        self.txt_estoque_atual.grid(row=0, column=1, padx=3, pady=5)
        self.txt_estoque_atual.insert(0, "0.00")

        ctk.CTkLabel(frame_preco, text="Est. Mínimo (UN):").grid(row=0, column=2, padx=3, pady=5)
        self.txt_estoque_min = ctk.CTkEntry(frame_preco, width=75)
        self.txt_estoque_min.grid(row=0, column=3, padx=3, pady=5)
        self.txt_estoque_min.insert(0, "0.00")

        ctk.CTkLabel(frame_preco, text="Custo:").grid(row=0, column=4, padx=3, pady=5)
        self.txt_calc_custo = ctk.CTkEntry(frame_preco, width=75)
        self.txt_calc_custo.grid(row=0, column=5, padx=3, pady=5)
        self.txt_calc_custo.insert(0, "0.00")
        self.txt_calc_custo.bind("<KeyRelease>", self.ao_alterar_custo_manual_criar)

        ctk.CTkLabel(frame_preco, text="Mínimo:").grid(row=0, column=6, padx=3, pady=5)
        self.txt_calc_min = ctk.CTkEntry(frame_preco, width=75)
        self.txt_calc_min.grid(row=0, column=7, padx=3, pady=5)
        self.txt_calc_min.bind("<KeyRelease>", self.recalcular_precos_venda)

        ctk.CTkLabel(frame_preco, text="Máximo:").grid(row=0, column=8, padx=3, pady=5)
        self.txt_calc_max = ctk.CTkEntry(frame_preco, width=75)
        self.txt_calc_max.grid(row=0, column=9, padx=3, pady=5)
        self.txt_calc_max.bind("<KeyRelease>", self.recalcular_precos_venda)

        self.lbl_res_calculo = ctk.CTkLabel(frame_preco, text="[ Custo: R$ 0.00 | Mín: R$ 0.00 | Máx: R$ 0.00 ]", font=("Arial", 12, "bold"), text_color="cyan")
        self.lbl_res_calculo.grid(row=0, column=10, padx=8, pady=5)

        self.btn_salvar_tudo = ctk.CTkButton(self, text="Salvar Novo Item", command=self.salvar_composto, fg_color="green", font=("Arial", 14, "bold"))
        self.btn_salvar_tudo.pack(pady=10)

    def limpar_campos(self):
        self.txt_nome_base.delete(0, 'end')
        self.txt_peso.delete(0, 'end')
        self.txt_estoque_atual.delete(0, 'end')
        self.txt_estoque_atual.insert(0, "0.00")
        self.txt_estoque_min.delete(0, 'end')
        self.txt_estoque_min.insert(0, "0.00")
        self.txt_calc_custo.delete(0, 'end')
        self.txt_calc_custo.insert(0, "0.00")
        self.txt_calc_min.delete(0, 'end')
        self.txt_calc_max.delete(0, 'end')
        self.cmb_unidade.set("kg")
        self.atualizar_sugestao()

        for linha in self.ingredientes_linhas:
            linha['frame'].destroy()
        self.ingredientes_linhas.clear()

    def atualizar_sugestao(self, event=None):
        nome = self.txt_nome_base.get().strip()
        peso = self.txt_peso.get().strip()
        un = self.cmb_unidade.get()

        if nome and peso:
            sugestao = f"{nome} {peso} {un}"
        elif nome:
            sugestao = nome
        else:
            sugestao = "-"

        self.lbl_sugestao.configure(text=f"Como irá ficar a descrição: {sugestao}")

    def adicionar_linha_ingrediente(self):
        row_frame = ctk.CTkFrame(self.frame_ingredientes)
        row_frame.pack(fill="x", pady=3)

        txt_busca = ctk.CTkEntry(row_frame, width=150, placeholder_text="ID / Nome...")
        txt_busca.pack(side="left", padx=5)

        cmb_ing = ctk.CTkOptionMenu(row_frame, values=["Digite e clique em Buscar"], width=250)
        cmb_ing.pack(side="left", padx=5)

        dict_linha = {
            'frame': row_frame,
            'txt_busca': txt_busca,
            'cmb_ing': cmb_ing,
            'custo_parcial': 0.0,
            'produtos_encontrados': {}
        }

        btn_buscar = ctk.CTkButton(
            row_frame, text="🔍 Buscar", width=80,
            command=lambda: self.buscar_ingredientes_db(txt_busca.get(), cmb_ing, dict_linha)
        )
        btn_buscar.pack(side="left", padx=5)

        txt_qtd = ctk.CTkEntry(row_frame, width=80, placeholder_text="Qtd")
        txt_qtd.pack(side="left", padx=5)

        cmb_un = ctk.CTkOptionMenu(row_frame, values=["kg", "g"], width=70)
        cmb_un.pack(side="left", padx=5)

        lbl_custo_info = ctk.CTkLabel(row_frame, text="R$ 0.00", font=("Arial", 11), width=120)
        lbl_custo_info.pack(side="left", padx=5)

        btn_remover = ctk.CTkButton(
            row_frame, text="X", width=35, fg_color="red", hover_color="darkred",
            command=lambda: self.remover_linha_ingrediente(dict_linha)
        )
        btn_remover.pack(side="left", padx=5)

        dict_linha.update({
            'txt_qtd': txt_qtd,
            'cmb_un': cmb_un,
            'lbl_custo': lbl_custo_info
        })

        txt_qtd.bind("<KeyRelease>", lambda e: self.recalcular_linha(dict_linha))
        txt_busca.bind("<Return>", lambda e: self.buscar_ingredientes_db(txt_busca.get(), cmb_ing, dict_linha))
        cmb_ing.configure(command=lambda e: self.recalcular_linha(dict_linha))
        cmb_un.configure(command=lambda e: self.recalcular_linha(dict_linha))

        self.ingredientes_linhas.append(dict_linha)

    def buscar_ingredientes_db(self, termo, cmb_widget, dict_linha):
        termo_clean = termo.strip()
        if not termo_clean:
            return

        try:
            with get_connection() as conn:
                cur = conn.cursor()

                if termo_clean.isdigit():
                    query = """
                        SELECT ID, DESCRICAO, PRECO_CUSTO FROM INGREDIENTE 
                        WHERE ID = ? OR UPPER(DESCRICAO) LIKE UPPER(?) 
                        ORDER BY DESCRICAO
                    """
                    cur.execute(query, (int(termo_clean), f"%{termo_clean}%"))
                else:
                    query = """
                        SELECT ID, DESCRICAO, PRECO_CUSTO FROM INGREDIENTE 
                        WHERE UPPER(DESCRICAO) LIKE UPPER(?) 
                        ORDER BY DESCRICAO
                    """
                    cur.execute(query, (f"%{termo_clean}%",))

                res = cur.fetchall()

            if not res:
                cmb_widget.configure(values=["Nenhum item encontrado"])
                dict_linha['produtos_encontrados'] = {}
                return

            dict_linha['produtos_encontrados'] = {
                f"{row[1]} (ID: {row[0]})": {
                    "id": int(row[0]),
                    "pcompra": float(row[2]) if row[2] is not None else 0.0
                } for row in res
            }

            opcoes = list(dict_linha['produtos_encontrados'].keys())
            cmb_widget.configure(values=opcoes)
            cmb_widget.set(opcoes[0])
            self.recalcular_linha(dict_linha)

        except Exception as e:
            messagebox.showerror("Erro de Banco", f"Erro ao pesquisar ingrediente:\n{e}")

    def remover_linha_ingrediente(self, dict_linha):
        if dict_linha in self.ingredientes_linhas:
            self.ingredientes_linhas.remove(dict_linha)
            dict_linha['frame'].destroy()
            self.recalcular_custo_total()

    def recalcular_linha(self, dict_linha):
        prod_key = dict_linha['cmb_ing'].get()
        produtos = dict_linha.get('produtos_encontrados', {})

        if prod_key not in produtos:
            return

        pcompra = produtos[prod_key]['pcompra']
        try:
            qtd = float(dict_linha['txt_qtd'].get().replace(',', '.'))
            un = dict_linha['cmb_un'].get()

            fator = (qtd / 1000.0) if un == 'g' else qtd
            custo_parcial = fator * pcompra
            dict_linha['custo_parcial'] = custo_parcial

            dict_linha['lbl_custo'].configure(
                text=f"R$ {custo_parcial:.2f}"
            )
        except ValueError:
            dict_linha['custo_parcial'] = 0.0
            dict_linha['lbl_custo'].configure(text="R$ 0.00")

        self.recalcular_custo_total()

    def recalcular_custo_total(self):
        custo_total = sum(linha.get('custo_parcial', 0.0) for linha in self.ingredientes_linhas)
        self.lbl_custo_total.configure(text=f"Custo total do item: R$ {custo_total:.2f}")

        self.txt_calc_custo.delete(0, 'end')
        self.txt_calc_custo.insert(0, f"{custo_total:.2f}")

        self.ao_alterar_custo_manual_criar()

    def ao_alterar_custo_manual_criar(self, event=None):
        try:
            texto_custo = self.txt_calc_custo.get().replace(',', '.').strip()
            if texto_custo:
                custo = float(texto_custo)
                v_min = custo + 8.00
                v_max = v_min + 10.00

                self.txt_calc_min.delete(0, 'end')
                self.txt_calc_min.insert(0, f"{v_min:.2f}")

                self.txt_calc_max.delete(0, 'end')
                self.txt_calc_max.insert(0, f"{v_max:.2f}")
        except ValueError:
            pass

        self.recalcular_precos_venda()

    def recalcular_precos_venda(self, event=None):
        try:
            custo = float(self.txt_calc_custo.get().replace(',', '.'))
        except ValueError:
            custo = 0.0

        try:
            val_min = float(self.txt_calc_min.get().replace(',', '.'))
        except ValueError:
            val_min = 0.0

        try:
            val_max = float(self.txt_calc_max.get().replace(',', '.'))
        except ValueError:
            val_max = 0.0

        v_min = val_min
        v_max = val_max

        self.lbl_res_calculo.configure(
            text=f"[ Custo: R$ {custo:.2f} | Mín: R$ {v_min:.2f} | Máx: R$ {v_max:.2f} ]"
        )

    def salvar_composto(self):
        nome = self.txt_nome_base.get().strip()
        peso = self.txt_peso.get().strip()
        un_peso = self.cmb_unidade.get()

        if not nome or not peso:
            messagebox.showwarning("Campos Obrigatórios", "Preencha a Descrição e o Peso do novo item!")
            return

        try:
            est_atual = float(self.txt_estoque_atual.get().replace(',', '.').strip() or 0)
        except ValueError:
            est_atual = 0.0

        try:
            est_min = float(self.txt_estoque_min.get().replace(',', '.').strip() or 0)
        except ValueError:
            est_min = 0.0

        texto_custo_raw = self.txt_calc_custo.get().replace(',', '.').strip()
        try:
            custo_total = float(texto_custo_raw) if texto_custo_raw else 0.0
        except ValueError:
            custo_total = 0.0

        if custo_total <= 0:
            messagebox.showwarning("Campos Obrigatórios", "O Valor do Custo é obrigatório e deve ser maior que zero!")
            return

        espec_completa = f"{nome} {peso} {un_peso}"

        ingredientes_validos = []
        for dict_ing in self.ingredientes_linhas:
            prod_key = dict_ing['cmb_ing'].get()
            produtos = dict_ing.get('produtos_encontrados', {})
            if prod_key in produtos:
                try:
                    qtd = float(dict_ing['txt_qtd'].get().replace(',', '.'))
                except ValueError:
                    qtd = 0.0
                if qtd > 0:
                    ingredientes_validos.append((dict_ing, produtos[prod_key]['id'], qtd, dict_ing['cmb_un'].get()))

        tem_ingredientes = len(ingredientes_validos) > 0

        try:
            with get_connection() as conn:
                cur = conn.cursor()

                if not tem_ingredientes:
                    cur.execute("SELECT ID FROM INGREDIENTE WHERE UPPER(DESCRICAO) = UPPER(?)", (espec_completa,))
                    if cur.fetchone():
                        messagebox.showerror("Erro de Duplicidade", f"Já existe um ingrediente cadastrado como '{espec_completa}'!")
                        return

                    cur.execute("SELECT COALESCE(MAX(ID), 0) + 1 FROM INGREDIENTE")
                    novo_id_ing = int(cur.fetchone()[0])

                    cur.execute("""
                        INSERT INTO INGREDIENTE (ID, DESCRICAO, PRECO_CUSTO, ESTOQUE, ESTOQUEMIN)
                        VALUES (?, ?, ?, ?, ?)
                    """, (novo_id_ing, espec_completa, custo_total, est_atual, est_min))

                    conn.commit()
                    messagebox.showinfo("Sucesso", f"Ingrediente '{espec_completa}' cadastrado com sucesso!")

                else:
                    prevenda = float(self.txt_calc_min.get().replace(',', '.')) if self.txt_calc_min.get() else 0.0
                    pvenda = float(self.txt_calc_max.get().replace(',', '.')) if self.txt_calc_max.get() else 0.0

                    if prevenda < custo_total:
                        messagebox.showerror("Erro de Validação", "O Valor Mínimo não pode ser menor que o Custo Total!")
                        return
                    if pvenda < prevenda:
                        messagebox.showerror("Erro de Validação", "O Valor Máximo não pode ser menor que o Valor Mínimo!")
                        return

                    cur.execute("SELECT ID FROM PRODUTO WHERE UPPER(ESPEC) = UPPER(?)", (espec_completa,))
                    if cur.fetchone():
                        messagebox.showerror("Erro de Duplicidade", f"Já existe um produto cadastrado como '{espec_completa}'!")
                        return

                    cur.execute("SELECT COALESCE(MAX(ID), 0) + 1 FROM PRODUTO")
                    novo_produto_id = int(cur.fetchone()[0])

                    cur.execute("""
                    INSERT INTO PRODUTO (
                        ID, ESPEC, MARCA, ITEM, MEDIDA, PESOLQ, PESOBT, VOLUME, ADICIONAL,
                        PFORNEC, QUANT, PCOMPRA, MGVENDA, PVENDA, MGREVENDA, PREVENDA,
                        COMISSAO, ORIGEM, EANTRIB, UTRIB, QTRIB, CEST, NCM,
                        CFOP, CFOE, CST, CSOSN, CSTE, ALIQUOTA, ICMS,
                        EXTIPI, CSTIS, CSTIE, IPI, CSTPS, CSTPE, PIS, COFINS,
                        TRIBUTOS, INDEXM, PRODVINC, FORNEC, DATA, MODIF, UCOMPRA, UVENDA, UAJUSTE, NULO
                    )
                    VALUES (
                        ?, ?, '****', NULL, 'UN', 0.0, 0.0, 0.0, '',
                        0.0, 1.0, ?, 0.0, ?, 0.0, ?,
                        0.0, 0, '', '', 0.0, '', '',
                        '', '', '', '', '', 0.0, 0.0,
                        '', '', '', 0.0, '', '', 0.0, 0.0,
                        0.0, NULL, NULL, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, NULL, NULL, NULL, NULL
                    )
                    """, (novo_produto_id, espec_completa, custo_total, pvenda, prevenda))

                    cur.execute("SELECT COALESCE(MAX(ID), 0) + 1 FROM PRODUTO_COMPOSTO")
                    novo_composto_id = int(cur.fetchone()[0])

                    cur.execute("INSERT INTO PRODUTO_COMPOSTO (ID, PRODUTO_ID) VALUES (?, ?)", (novo_composto_id, novo_produto_id))

                    for dict_ing, ing_id, qtd, un in ingredientes_validos:
                        cur.execute("SELECT COALESCE(MAX(ID), 0) + 1 FROM FICHA_TECNICA")
                        novo_ft_id = int(cur.fetchone()[0])

                        cur.execute("""
                            INSERT INTO FICHA_TECNICA (ID, COMPOSTO_ID, INGREDIENTE_ID, QUANTIDADE, UNIDADE)
                            VALUES (?, ?, ?, ?, ?)
                        """, (novo_ft_id, novo_composto_id, ing_id, qtd, un))

                    cur.execute("""
                        INSERT INTO ESTOQUE (FIRMA, PRODUTO, ESTOQEXP, ESTOQMIN, ESTOQDEP, ESTOQCSM, ESTOQTFM, ESTOQANT, ESTOQAUD, SITUACAO, UAUDIT)
                        VALUES (1, ?, ?, ?, 0, 0, 0, 0, 0, 0, NULL)
                    """, (novo_produto_id, est_atual, est_min))

                    conn.commit()
                    messagebox.showinfo("Sucesso", f"Produto '{espec_completa}' e sua Ficha Técnica cadastrados com sucesso!")

            self.limpar_campos()
            self.controller.show_consulta()

        except Exception as e:
            messagebox.showerror("Erro de Cadastro", f"Falha ao cadastrar item:\n{e}")


if __name__ == "__main__":
    app = AppSistema()
    app.mainloop()