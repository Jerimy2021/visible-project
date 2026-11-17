from visible.domain.usuarios import ROSTER_PILOTO, item_usuario, resolver_id


def test_unifica_alias_miguel():
    # El bug de la Power App: 3 grafías = 3 personas. Aquí = 1 usuario.
    usuarios = [
        {
            "id": "u-miguel",
            "alias": [
                "Miguel Guzmán",
                "Miguel Guzmán Millones",
                "Miguel Angel Guzman Millones",
            ],
        }
    ]
    ids = {
        resolver_id("Miguel Guzmán", usuarios),
        resolver_id("Miguel Guzmán Millones", usuarios),
        resolver_id("Miguel Angel Guzman Millones", usuarios),
    }
    assert ids == {"u-miguel"}


def test_roster_piloto():
    ids = {u["id"] for u in ROSTER_PILOTO}
    assert ids == {"u-gponte", "u-jchanta"}
    # Gianella aparece con otra grafía en AprobacionesMes -> debe resolver igual.
    assert resolver_id("Gianella Arcela Ponte Carrasco", ROSTER_PILOTO) == "u-gponte"
    assert resolver_id("Jose Manuel Chanta Torres", ROSTER_PILOTO) == "u-jchanta"


def test_item_usuario_omite_telefono_vacio():
    item = item_usuario(ROSTER_PILOTO[0])
    assert "telefono_whatsapp" not in item
    assert item["rol"] == "Administrador"
